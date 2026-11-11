"""Step `evaluate`: evaluation -> reports/04_evaluation.md and reports/audit.csv. STOP for review after this step.

1. Coverage and bias by department.
2. Temporal link prediction: layers from publications with year <= T (T = current_year - years_back), target = new
   co-authorships in (T, current_year] among pairs without co-authorship up to T. AUC-PR and precision@k per layer,
   composite and baselines (random, same SSD, same department). Per layer the evaluation universe is the set of pairs
   where both people have the layer available at T; a NaN score inside that universe (e.g. a non-candidate `sem`
   pair) counts as the lowest score.
3. Convergent validity: Spearman correlations between layers on shared non-NaN pairs.
4. Embedding model comparison (if `embed --alt` was run): temporal AUC-PR of `sem` and same-SSD retrieval P@10.
5. Manual audit sheet: random people x top composite neighbours with evidence, empty `judgment` column.
Bootstrap 95% CIs resample PEOPLE (pairs are dependent through their endpoints).
"""

from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from . import config, layers
from .graph import edge_composite
from .layers import LAYERS

log = logging.getLogger(__name__)


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> list[str]:
    cols = list(df.columns)
    fmt = lambda v: floatfmt.format(v) if isinstance(v, (float, np.floating)) and not pd.isna(v) else ("" if pd.isna(v) else str(v))
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return lines


def precision_at_k(y: np.ndarray, s: np.ndarray, k: int) -> float:
    top = np.argsort(-s, kind="stable")[:k]
    return float(y[top].mean()) if len(top) else np.nan


def bootstrap_people(metric, y: np.ndarray, s: np.ndarray, pi: np.ndarray, pj: np.ndarray, n_people: int, reps: int, rng) -> tuple[float, float]:
    vals = []
    for _ in range(reps):
        keep = np.zeros(n_people, dtype=bool)
        keep[rng.integers(0, n_people, n_people)] = True
        m = keep[pi] & keep[pj]
        if m.sum() and y[m].sum():
            vals.append(metric(y[m], s[m]))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (np.nan, np.nan)


def coverage(inp: layers.Inputs, res: layers.Result) -> list[str]:
    people = inp.people.merge(res.availability, on="person_id")
    cols = [f"has_{l}" for l in LAYERS]
    by_dept = people.groupby(people.dept_name.fillna("(none)"))[cols].mean()
    by_dept.insert(0, "n", people.groupby(people.dept_name.fillna("(none)")).size())
    pa = inp.authorship.merge(inp.people[["person_id", "dept_name"]], on="person_id").merge(inp.pubs, on="pub_id")
    pub_stats = pa.groupby(pa.dept_name.fillna("(none)")).agg(
        pubs=("pub_id", "nunique"), abstract=("abstract", lambda s: s.notna().mean()), doi=("doi", lambda s: s.notna().mean()),
        linked=("openalex_id", lambda s: s.notna().mean()),
        languages=("abstract_lang", lambda s: ", ".join(f"{k} {v:.0%}" for k, v in s.value_counts(normalize=True).head(3).items())))
    md = ["## 1. Coverage by department\n", "Share of people with each layer available:\n",
          *md_table(by_dept.reset_index().rename(columns={"dept_name": "department"})),
          "\nPublication-level rates (people-publication rows):\n", *md_table(pub_stats.reset_index().rename(columns={"dept_name": "department"}))]
    return md


def _pairs(n: int):
    return np.triu_indices(n, 1)


def temporal(cfg: dict, inp: layers.Inputs, rng, alt: layers.Inputs | None = None) -> tuple[list[str], dict]:
    E = cfg["evaluation"]
    T = inp.current_year - E["years_back"]
    res_T = layers.compute(cfg, inp, year_max=T)
    n = len(res_T.people)
    pi, pj = _pairs(n)
    shared_T = res_T.raw["coauth"][pi, pj] > 0
    # co-authorships after T (in-press counts as current)
    idx = {p: i for i, p in enumerate(res_T.people)}
    later = inp.pubs[inp.pubs.year.isna() | (inp.pubs.year.astype(float) > T)]
    auth = inp.authorship[inp.authorship.pub_id.isin(later.pub_id) & inp.authorship.person_id.isin(idx)]
    shared_after = np.zeros((n, n), dtype=bool)
    for _, grp in auth.groupby("pub_id"):
        ids = [idx[p] for p in grp.person_id]
        for a in ids:
            for b in ids:
                if a != b:
                    shared_after[a, b] = True
    y_all = shared_after[pi, pj] & ~shared_T
    universe = ~shared_T
    log.info("temporal: T=%d, candidate pairs %d, new co-authorships %d", T, universe.sum(), y_all.sum())

    P_T = {l: layers.percentiles(res_T.raw[l]) for l in LAYERS}
    use_conf = cfg.get("confidence", {}).get("weight_composite", False)
    comp_plain = layers.composite(P_T, cfg["weights"])
    comp_conf = layers.composite(P_T, cfg["weights"], {"sem": res_T.sem_conf}) if res_T.sem_conf is not None else comp_plain
    comp = comp_conf if use_conf else comp_plain
    avail = res_T.availability
    scores = {l: res_T.raw[l][pi, pj] for l in LAYERS}
    scores["composite"] = comp[pi, pj]
    scores["composite (confidence-weighted)" if not use_conf else "composite (no confidence)"] = (comp_conf if not use_conf else comp_plain)[pi, pj]
    if alt is not None:
        scores["sem_alt"] = layers.compute(cfg, alt, year_max=T).raw["sem"][pi, pj]
    ssd = inp.people.ssd.astype(object).where(inp.people.ssd.notna(), None).to_numpy()
    dept = inp.people.dept_id.astype(object).where(inp.people.dept_id.notna(), None).to_numpy()
    scores["baseline_random"] = rng.random(len(pi))
    scores["baseline_same_ssd"] = ((ssd[pi] == ssd[pj]) & (ssd[pi] != None)).astype(float)  # noqa: E711
    scores["baseline_same_dept"] = ((dept[pi] == dept[pj]) & (dept[pi] != None)).astype(float)  # noqa: E711

    def metrics(name: str, s: np.ndarray, m: np.ndarray) -> dict:
        y, sc = y_all[m].astype(int), np.nan_to_num(s[m], nan=-1.0)
        if y.sum() == 0 or m.sum() == 0:
            return {"scorer": name, "pairs": int(m.sum()), "positives": int(y.sum())}
        row = {"scorer": name, "pairs": int(m.sum()), "positives": int(y.sum()), "prevalence": float(y.mean()),
               "AUC-PR": float(average_precision_score(y, sc))}
        lo, hi = bootstrap_people(average_precision_score, y, sc, pi[m], pj[m], n, E["bootstrap_reps"], rng)
        row["AUC-PR 95% CI"] = f"[{lo:.3f}, {hi:.3f}]"
        for k in E["precision_k"]:
            row[f"P@{k}"] = precision_at_k(y, sc, k)
        return row

    rows = []
    for name, s in scores.items():
        if name == "coauth":   # identically 0 on pairs without co-authorship up to T: not a predictor here
            continue
        if name in LAYERS or name == "sem_alt":
            a = avail[f"has_{'sem' if name == 'sem_alt' else name}"].to_numpy()
            m = universe & a[pi] & a[pj]
        elif name.startswith("composite"):
            m = universe & ~np.isnan(s)
        else:
            m = universe
        rows.append(metrics(name, s, m))
    # does "more publications, better" hold? sem split by the smaller of the two people's embedded-publication counts
    a = avail["has_sem"].to_numpy()
    n_emb = avail["n_pubs_embedded"].to_numpy()
    low = np.minimum(n_emb[pi], n_emb[pj])
    for label, sel in (("sem [both >= 20 abstracts]", low >= 20), ("sem [smaller of the two < 20 abstracts]", low < 20)):
        rows.append(metrics(label, scores["sem"], universe & a[pi] & a[pj] & sel))
    md = [f"## 2. Temporal link prediction (T = {T})\n",
          f"Target: new co-authorships in ({T}, {inp.current_year}] among {int(universe.sum())} pairs without co-authorship up to {T}: "
          f"{int(y_all.sum())} positives. Bootstrap: {E['bootstrap_reps']} resamples of people.\n", *md_table(pd.DataFrame(rows))]
    return md, {"T": T, "rows": rows}


def convergent(res: layers.Result) -> list[str]:
    n = len(res.people)
    pi, pj = _pairs(n)
    df = pd.DataFrame({l: res.raw[l][pi, pj] for l in LAYERS})
    corr = df.corr(method="spearman")
    counts = pd.DataFrame({a: {b: int((df[a].notna() & df[b].notna()).sum()) for b in LAYERS} for a in LAYERS})
    return ["## 3. Convergent validity (Spearman, pairwise complete)\n", *md_table(corr.reset_index().rename(columns={"index": "layer"})),
            "\nNumber of shared non-NaN pairs:\n", *md_table(counts.reset_index().rename(columns={"index": "layer"}), "{:d}")]


def ssd_precision_at_10(inp: layers.Inputs, res: layers.Result, rng, reps: int) -> tuple[float, float, float, int]:
    ssd = inp.people.ssd.astype(object).where(inp.people.ssd.notna(), None).to_numpy()
    ok = res.eligible_sem & (ssd != None)  # noqa: E711
    C = res.centroids[ok]
    s = ssd[ok]
    cos = C @ C.T
    np.fill_diagonal(cos, -np.inf)
    k = min(10, len(s) - 1)
    if k < 1:
        return np.nan, np.nan, np.nan, int(ok.sum())
    top = np.argsort(-cos, axis=1)[:, :k]
    prec = (s[top] == s[:, None]).mean(1)
    boots = [prec[rng.integers(0, len(prec), len(prec))].mean() for _ in range(reps)]
    return float(prec.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)), int(ok.sum())


def embedding_comparison(cfg: dict, inp: layers.Inputs, res: layers.Result, alt: layers.Inputs | None, alt_res: layers.Result | None,
                         temporal_rows: list[dict], rng) -> list[str]:
    reps = cfg["evaluation"]["bootstrap_reps"]
    rows = []
    for name, model, i, r in (("primary", cfg["embedding"]["model"], inp, res), ("alt", cfg["embedding_alt"]["model"], alt, alt_res)):
        if i is None:
            continue
        m, lo, hi, n_ok = ssd_precision_at_10(i, r, rng, reps)
        ap = next((x.get("AUC-PR") for x in temporal_rows if x["scorer"] == ("sem" if name == "primary" else "sem_alt")), np.nan)
        rows.append({"model": model, "people": n_ok, "same-SSD P@10": m, "P@10 95% CI": f"[{lo:.3f}, {hi:.3f}]", "temporal AUC-PR (sem)": ap})
    md = ["## 4. Embedding model comparison\n"]
    if len(rows) < 2:
        md.append(f"Only the primary model is available. Run `python -m unitn_net embed --alt` (tag `{cfg['embedding_alt']['tag']}`) to compare.\n")
    return md + md_table(pd.DataFrame(rows))


def audit_sheet(cfg: dict, inp: layers.Inputs, rng) -> int:
    E = cfg["evaluation"]
    edges = pd.read_parquet(config.PROCESSED / "edges.parquet")
    edges["composite"] = edge_composite(edges, cfg["weights"], cfg.get("confidence", {}).get("weight_composite", False))
    names = dict(zip(inp.people.person_id, inp.people.given_name + " " + inp.people.family_name))
    both = pd.concat([edges, edges.rename(columns={"person_i": "person_j", "person_j": "person_i"})], ignore_index=True)
    sample = rng.choice(inp.people.person_id.to_numpy(), size=min(E["audit_people"], len(inp.people)), replace=False)
    rows = []
    for p in sample:
        top = both[both.person_i == p].sort_values("composite", ascending=False).head(E["audit_neighbours"])
        for r in top.itertuples():
            ev = json.loads(r.evidence)
            summary = []
            for l in LAYERS:
                if l in ev and ev[l]:
                    summary.append(f"{l}: {json.dumps(ev[l], ensure_ascii=False)[:300]}")
            rows.append({"person_id": p, "person": names.get(p), "neighbour_id": r.person_j, "neighbour": names.get(r.person_j),
                         "composite": round(float(r.composite), 3), **{f"{l}_p": getattr(r, f"{l}_p") for l in LAYERS},
                         "evidence": " || ".join(summary), "judgment": ""})
    pd.DataFrame(rows).to_csv(config.REPORTS / "audit.csv", index=False)
    return len(rows)


def run(cfg: dict, args=None) -> None:
    config.ensure_dirs()
    rng = np.random.default_rng(cfg["evaluation"]["seed"])
    inp = layers.load_inputs(cfg)
    res = layers.compute(cfg, inp)
    tag = cfg["embedding_alt"].get("tag", "")
    alt = alt_res = None
    if tag and (config.PROCESSED / f"embeddings_{tag}.npy").exists():
        alt = layers.load_inputs(cfg, tag)
        alt_res = layers.compute(cfg, alt)
    md = ["# 04 Evaluation\n", f"People: {len(res.people)}; publications: {len(inp.pubs)}; current year: {inp.current_year}.\n"]
    md += coverage(inp, res)
    t_md, t = temporal(cfg, inp, rng, alt)
    md += ["", *t_md]
    md += ["", *convergent(res)]
    md += ["", *embedding_comparison(cfg, inp, res, alt, alt_res, t["rows"], rng)]
    n_audit = audit_sheet(cfg, inp, rng)
    md += ["", "## 5. Manual audit\n", f"`reports/audit.csv`: {n_audit} rows ({cfg['evaluation']['audit_people']} people x top-{cfg['evaluation']['audit_neighbours']} "
           "composite neighbours). Fill `judgment` (e.g. 1 = plausible, 0 = not)."]
    (config.REPORTS / "04_evaluation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("wrote reports/04_evaluation.md")
