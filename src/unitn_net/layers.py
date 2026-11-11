"""Step `layers`: similarity layers between pairs of people.

All layers are n x n float matrices over the in-scope people; NaN means "undefined for this pair", never 0.
Publications co-authored by i and j are EXCLUDED from `sem`, `coupling` and `direct` for the pair (i, j).
`sem` uses one vector per publication, the embedding of "<title>. <abstract>": publications without an abstract take no part.
`compute()` is pure (no I/O) so that evaluate.py can rerun it on a temporal cut (year_max).
Evidence for an edge is produced lazily by the callables in Result.evidence, only for selected edges.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.stats import rankdata

from . import config
from .textnorm import norm_text

log = logging.getLogger(__name__)
LAYERS = ["sem", "coupling", "direct", "coauth", "teach", "field"]


@dataclass
class Inputs:
    people: pd.DataFrame        # person_id, dept_id, ssd, cun, ...
    pubs: pd.DataFrame          # processed publications: pub_id, title, year, in_press, doi, openalex_id
    authorship: pd.DataFrame    # pub_id, person_id
    emb: np.ndarray             # L2-normalised rows
    emb_index: pd.DataFrame     # row, entity_type, entity_id, text_kind ("title_abstract" | "course")
    courses: pd.DataFrame       # course_id, name, degree_programme, academic_year
    teaching: pd.DataFrame      # course_id, person_id
    oa_refs: pd.DataFrame       # openalex_id, referenced_openalex_id
    current_year: int = field(default_factory=lambda: dt.date.today().year)


@dataclass
class Result:
    people: list[str]
    raw: dict[str, np.ndarray]
    availability: pd.DataFrame
    evidence: dict[str, Callable[[int, int], object]]
    centroids: np.ndarray       # sem centroids (rows of non-eligible people are zero)
    eligible_sem: np.ndarray
    sem_conf: np.ndarray | None = None   # n x n confidence of `sem` in [0, 1] (NaN where sem is undefined)


def load_inputs(cfg: dict, tag: str = "") -> Inputs:
    suffix = f"_{tag}" if tag else ""
    return Inputs(
        people=pd.read_parquet(config.INTERIM / "people.parquet"),
        pubs=pd.read_parquet(config.PROCESSED / "publications.parquet"),
        authorship=pd.read_parquet(config.PROCESSED / "authorship.parquet"),
        emb=np.load(config.PROCESSED / f"embeddings{suffix}.npy"),
        emb_index=pd.read_parquet(config.PROCESSED / f"embeddings_index{suffix}.parquet"),
        courses=pd.read_parquet(config.INTERIM / "courses.parquet"),
        teaching=pd.read_parquet(config.INTERIM / "teaching.parquet"),
        oa_refs=pd.read_parquet(config.PROCESSED / "oa_references.parquet"),
    )


def set_similarity(S: np.ndarray, wa: np.ndarray, wb: np.ndarray) -> float:
    """0.5 * (weighted mean_a max_b S + weighted mean_b max_a S) for a cosine matrix S (|a| x |b|)."""
    return 0.5 * (float(np.average(S.max(axis=1), weights=wa)) + float(np.average(S.max(axis=0), weights=wb)))


def composite(P: dict[str, np.ndarray] | pd.DataFrame, weights: dict[str, float],
              conf: dict[str, np.ndarray] | None = None) -> np.ndarray:
    """Weighted mean of percentile layers over the layers that are non-NaN for each pair (missing != 0).
    `conf[layer]` (optional, same shape as the layer) multiplies that layer's weight pair by pair: a layer known with low
    confidence counts less, it never counts as zero. Where conf is NaN the weight is unchanged."""
    num, den = None, None
    for layer, w in weights.items():
        if layer not in P:
            continue
        p = np.asarray(P[layer], dtype=float)
        ok = ~np.isnan(p)
        wl = w
        if conf is not None and layer in conf:
            c = np.asarray(conf[layer], dtype=float)
            wl = w * np.where(np.isnan(c), 1.0, c)
        contrib, wsum = np.where(ok, p * wl, 0.0), np.where(ok, wl, 0.0)
        num = contrib if num is None else num + contrib
        den = wsum if den is None else den + wsum
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    return np.where(den > 0, out, np.nan)


def percentiles(M: np.ndarray) -> np.ndarray:
    """Percentile rank (average ranks for ties) over the non-NaN upper-triangle pairs; symmetric; NaN kept."""
    n = M.shape[0]
    P = np.full_like(M, np.nan, dtype=float)
    iu, ju = np.triu_indices(n, 1)
    v = M[iu, ju]
    ok = np.isfinite(v)
    if ok.any():
        r = rankdata(v[ok], method="average") / ok.sum()
        P[iu[ok], ju[ok]] = r
        P[ju[ok], iu[ok]] = r
    return P


def _minmax(M: np.ndarray) -> np.ndarray:
    ok = np.isfinite(M)
    if not ok.any():
        return M
    lo, hi = M[ok].min(), M[ok].max()
    return np.where(ok, (M - lo) / (hi - lo) if hi > lo else 0.0, np.nan)


def compute(cfg: dict, inp: Inputs, year_max: int | None = None) -> Result:
    L = cfg["layers"]
    people = inp.people.person_id.astype(str).tolist()
    n = len(people)
    idx = {p: i for i, p in enumerate(people)}
    cy = inp.current_year

    pubs = inp.pubs
    if year_max is not None:
        pubs = pubs[pubs.year.notna() & (pubs.year.astype(float) <= year_max)]
    pub_ids = pubs.pub_id.astype(str).tolist()
    pidx = {p: k for k, p in enumerate(pub_ids)}
    year_of = dict(zip(pub_ids, pubs.year.astype(float)))
    title_of = dict(zip(pub_ids, pubs.title))
    doi_of = dict(zip(pub_ids, pubs.doi))
    auth = inp.authorship[inp.authorship.person_id.astype(str).isin(idx) & inp.authorship.pub_id.astype(str).isin(pidx)]
    ai = auth.person_id.astype(str).map(idx).to_numpy()
    aj = auth.pub_id.astype(str).map(pidx).to_numpy()
    A = sp.csr_matrix((np.ones(len(auth)), (ai, aj)), shape=(n, max(len(pub_ids), 1)))
    A.data[:] = 1.0
    pubs_of = [set(pub_ids[k] for k in A.indices[A.indptr[i]:A.indptr[i + 1]]) for i in range(n)]
    shared = (A @ A.T).toarray()
    np.fill_diagonal(shared, 0)
    coauth_pairs = [(i, j) for i, j in zip(*np.nonzero(np.triu(shared)))]

    def weight(pub: str) -> float:
        y = year_of.get(pub)
        y = cy if y is None or np.isnan(y) else y
        return float(np.exp(-(cy - y) / L["recency_tau"])) if L["recency_tau"] > 0 else 1.0

    # ---------------- sem ----------------
    # Within-language (`layers.sem_within_language`): only publications of the same language group ('it', 'en') are ever
    # compared; a pair's score is the mean of the per-language set similarities weighted by min(#pubs_i, #pubs_j) in that
    # language, and it is NaN when the two people share no language with >= min_papers_sem publications each.
    E = inp.emb
    ei = inp.emb_index[(inp.emb_index.entity_type == "publication") & (inp.emb_index.text_kind == "title_abstract")]
    row_of_pub = {str(e): int(r) for e, r in zip(ei.entity_id, ei.row) if str(e) in pidx}   # only publications with an abstract
    within = bool(L.get("sem_within_language", False)) and "text_lang" in pubs.columns
    lang_of = dict(zip(pub_ids, pubs["text_lang"])) if within else {}
    groups = ["it", "en"] if within else [None]
    min_p = L["min_papers_sem"]
    emb_pubs = [sorted(p for p in pubs_of[i] if p in row_of_pub) for i in range(n)]
    n_emb = np.array([len(x) for x in emb_pubs])
    d = E.shape[1] if E.ndim == 2 else 0

    def in_group(p: str, g) -> bool:
        return g is None or lang_of.get(p) == g

    def centroid(i: int, g) -> np.ndarray:
        ps = [p for p in emb_pubs[i] if in_group(p, g)]
        w = np.array([weight(p) for p in ps])
        c = (E[[row_of_pub[p] for p in ps]] * w[:, None]).sum(0)
        return c / (np.linalg.norm(c) or 1.0)

    half = float(cfg.get("confidence", {}).get("half_evidence", 5.0))

    def person_conf(i: int, g) -> float:
        """n / (n + half_evidence), n = the person's abstracts in language g: a heuristic, not calibrated on data."""
        x = float(sum(in_group(p, g) for p in emb_pubs[i]))
        return x / (x + half)

    # Calibration (`layers.sem_calibrate`): a cosine means different things per language (random pairs of abstracts: mean 0.20 in
    # English, 0.25 in Italian, measured 2026-09-30), so each cosine is replaced by its percentile among random pairs of abstracts
    # of the SAME language: "how unusual is this similarity", comparable across languages.
    calibrate = bool(L.get("sem_calibrate", False))
    tables: dict = {}
    if calibrate:
        rng_c = np.random.default_rng(0)
        for g in groups:
            pool = np.array([r for p, r in row_of_pub.items() if in_group(p, g)])
            if len(pool) < 200:
                continue
            a_, b_ = rng_c.choice(pool, 200_000), rng_c.choice(pool, 200_000)
            keep = a_ != b_
            tables[g] = np.sort(np.einsum("ij,ij->i", E[a_[keep]], E[b_[keep]]))

    def calib(S: np.ndarray, g) -> np.ndarray:
        tb = tables.get(g)
        return S if tb is None else np.searchsorted(tb, S, side="right") / len(tb)

    Cg, elig_g = {}, {}
    for g in groups:
        cnt = np.array([sum(in_group(p, g) for p in emb_pubs[i]) for i in range(n)])
        elig_g[g] = cnt >= min_p
        Cg[g] = np.zeros((n, d), dtype=np.float32)
        for i in np.flatnonzero(elig_g[g]):
            Cg[g][i] = centroid(i, g)
    eligible = np.any([elig_g[g] for g in groups], axis=0)
    C = np.zeros((n, d), dtype=np.float32)          # overall centroid, kept for evaluation / layout
    for i in np.flatnonzero(n_emb >= min_p):
        C[i] = centroid(i, None)

    def own(i: int, j: int) -> list[str]:
        sh = pubs_of[i] & pubs_of[j]
        return [p for p in emb_pubs[i] if p not in sh]

    def sem_pair(i: int, j: int) -> tuple[float, list, float]:
        oi, oj = own(i, j), own(j, i)
        scores, weights, cand, confs = [], [], [], []
        for g in groups:
            a, b = [p for p in oi if in_group(p, g)], [p for p in oj if in_group(p, g)]
            if len(a) < min_p or len(b) < min_p:
                continue
            S = E[[row_of_pub[p] for p in a]] @ E[[row_of_pub[p] for p in b]].T          # raw cosines (shown as evidence)
            Sc = calib(S, g)                                                               # scored on the calibrated scale
            scores.append(set_similarity(np.clip(Sc, 0.0, 1.0), np.array([weight(p) for p in a]), np.array([weight(p) for p in b])))
            weights.append(min(len(a), len(b)))
            confs.append(min(person_conf(i, g), person_conf(j, g)))   # weakest link
            for r, c in zip(*np.unravel_index(np.argsort(-Sc, axis=None)[:3], Sc.shape)):
                cand.append((float(Sc[r, c]), float(S[r, c]), a[r], b[c], g))
        if not scores:
            return np.nan, [], np.nan
        cand.sort(key=lambda x: -x[0])
        ev = [{"a": title_of[pa], "b": title_of[pb], "doi_a": _none(doi_of[pa]), "doi_b": _none(doi_of[pb]),
               "cos": round(min(raw, 1.0), 3), **({"lang": g} if g else {})} for _, raw, pa, pb, g in cand[:3]]
        return float(np.average(scores, weights=weights)), ev, float(np.average(confs, weights=weights))

    sem = np.full((n, n), np.nan)
    pairs: set[tuple[int, int]] = set()
    for g in groups:
        el = elig_g[g]
        if el.sum() < 2:
            continue
        cos = Cg[g] @ Cg[g].T
        cos[~el, :] = -np.inf
        cos[:, ~el] = -np.inf
        np.fill_diagonal(cos, -np.inf)
        k = min(L["sem_candidates"], n - 1)
        for i in np.flatnonzero(el):
            top = np.argpartition(-cos[i], k - 1)[:k] if k < n else np.arange(n)
            pairs.update((min(i, j), max(i, j)) for j in top if np.isfinite(cos[i, j]))
    sem_conf = np.full((n, n), np.nan)
    for i, j in pairs:
        s, _, c = sem_pair(i, j)
        sem[i, j] = sem[j, i] = s
        sem_conf[i, j] = sem_conf[j, i] = c
    person_sem_conf = np.array([max(person_conf(i, g) for g in groups) if eligible[i] else np.nan for i in range(n)])

    # ---------------- coupling & direct ----------------
    work_of_pub = {p: str(w) for p, w in zip(pub_ids, pubs.openalex_id) if pd.notna(w)}
    works = sorted(set(work_of_pub.values()))
    widx = {w: k for k, w in enumerate(works)}
    W = sp.lil_matrix((n, max(len(works), 1)))
    for i in range(n):
        for p in pubs_of[i]:
            if p in work_of_pub:
                W[i, widx[work_of_pub[p]]] = 1.0
    W = W.tocsr()
    refs = inp.oa_refs[inp.oa_refs.openalex_id.astype(str).isin(widx)]
    ref_ids = sorted(set(refs.referenced_openalex_id.astype(str)))
    ridx = {r: k for k, r in enumerate(ref_ids)}
    R = sp.csr_matrix((np.ones(len(refs)), (refs.openalex_id.astype(str).map(widx).to_numpy(),
                                             refs.referenced_openalex_id.astype(str).map(ridx).to_numpy())),
                      shape=(max(len(works), 1), max(len(ref_ids), 1)))
    R.data[:] = 1.0
    df = np.asarray(R.sum(axis=0)).ravel()
    idf = np.log(max(len(works), 1) / np.maximum(df, 1.0))
    idf_diag = sp.diags(idf)
    shared_works = {(i, j): {work_of_pub[p] for p in pubs_of[i] & pubs_of[j] if p in work_of_pub} for i, j in coauth_pairs}

    def ref_vector(i: int, exclude: set[str]) -> sp.csr_matrix:
        wi = W[i].tolil()
        for w in exclude:
            wi[0, widx[w]] = 0.0
        return (wi.tocsr() @ R) @ idf_diag

    V = (W @ R) @ idf_diag
    norms = np.sqrt(np.asarray(V.multiply(V).sum(axis=1)).ravel())
    has_refs = norms > 0
    Vn = sp.diags(np.where(has_refs, 1.0 / np.where(has_refs, norms, 1.0), 0.0)) @ V
    coupling = (Vn @ Vn.T).toarray()
    coupling[~has_refs, :] = np.nan
    coupling[:, ~has_refs] = np.nan
    np.fill_diagonal(coupling, np.nan)

    internal = refs[refs.referenced_openalex_id.astype(str).isin(widx)]  # citations within the corpus
    Rc = sp.csr_matrix((np.ones(len(internal)), (internal.openalex_id.astype(str).map(widx).to_numpy(),
                                                  internal.referenced_openalex_id.astype(str).map(widx).to_numpy())),
                       shape=(max(len(works), 1), max(len(works), 1)))
    Rc.data[:] = 1.0
    cnt = (W @ Rc @ W.T).toarray()
    has_works = np.asarray(W.sum(axis=1)).ravel() > 0
    D = cnt + cnt.T
    np.fill_diagonal(D, 0)

    def coupling_pair(i: int, j: int):
        vi, vj = ref_vector(i, shared_works[(i, j)]), ref_vector(j, shared_works[(i, j)])
        ni, nj = np.sqrt(vi.multiply(vi).sum()), np.sqrt(vj.multiply(vj).sum())
        if ni == 0 or nj == 0:
            return np.nan
        return float((vi @ vj.T).toarray()[0, 0] / (ni * nj))

    for i, j in coauth_pairs:
        if has_refs[i] and has_refs[j]:
            coupling[i, j] = coupling[j, i] = coupling_pair(i, j)
        if has_works[i] and has_works[j]:
            wi = W[i].tolil()
            wj = W[j].tolil()
            for w in shared_works[(i, j)]:
                wi[0, widx[w]] = 0.0
                wj[0, widx[w]] = 0.0
            wi, wj = wi.tocsr(), wj.tocsr()
            if wi.nnz == 0 or wj.nnz == 0:
                D[i, j] = D[j, i] = np.nan
            else:
                D[i, j] = D[j, i] = float((wi @ Rc @ wj.T).toarray()[0, 0] + (wj @ Rc @ wi.T).toarray()[0, 0])
    direct = np.log1p(D.astype(float))
    direct[~has_works, :] = np.nan
    direct[:, ~has_works] = np.nan
    np.fill_diagonal(direct, np.nan)
    direct = _minmax(direct)

    # ---------------- coauth ----------------
    coauth = np.log1p(shared.astype(float))
    coauth = coauth / coauth.max() if coauth.max() > 0 else coauth
    np.fill_diagonal(coauth, np.nan)

    # ---------------- teach ----------------
    # Three plain components, averaged with the `[teach]` weights over the ones that are defined for the pair:
    #   co_teaching: 1 - 0.5^k, k = distinct courses (same course record: year, name, programme) taught by both;
    #   programmes : Jaccard of the degree programmes the two people teach in;
    #   content    : cosine between the centroids of the embedded course descriptions ("<name>. <description>"; a course
    #                without a real description has no vector, so `content` is undefined, not zero, when either has none).
    TW = {"co_teaching": 0.3, "programmes": 0.3, "content": 0.4, **cfg.get("teach", {})}
    ci = inp.emb_index[inp.emb_index.entity_type == "course"]
    row_of_course = {str(e): int(r) for e, r in zip(ci.entity_id, ci.row)}
    course_name = dict(zip(inp.courses.course_id.astype(str), inp.courses.name))
    course_prog = dict(zip(inp.courses.course_id.astype(str), inp.courses.degree_programme))
    courses_of: list[list[str]] = [[] for _ in range(n)]
    for c, p in zip(inp.teaching.course_id.astype(str), inp.teaching.person_id.astype(str)):
        if p in idx and c in course_name and c not in courses_of[idx[p]]:
            courses_of[idx[p]].append(c)
    has_courses = np.array([len(c) > 0 for c in courses_of])
    described_of = [[c for c in cs if c in row_of_course] for cs in courses_of]
    has_desc = np.array([len(c) > 0 for c in described_of])
    Cc = np.zeros((n, d), dtype=np.float32)
    for i in np.flatnonzero(has_desc):
        c = E[[row_of_course[x] for x in described_of[i]]].mean(0)
        Cc[i] = c / (np.linalg.norm(c) or 1.0)
    content = np.clip(Cc @ Cc.T, 0.0, 1.0).astype(float)   # clipped so that every layer lives in [0, 1]
    content[~has_desc, :] = np.nan
    content[:, ~has_desc] = np.nan

    def _incidence(sets: list[set]) -> np.ndarray:
        keys = {k: q for q, k in enumerate(sorted(set().union(*sets)))} if n else {}
        M = sp.lil_matrix((n, max(len(keys), 1)))
        for i, ks in enumerate(sets):
            for k in ks:
                M[i, keys[k]] = 1.0
        return M.tocsr()

    progs_of = [{course_prog[c] for c in courses_of[i] if pd.notna(course_prog[c])} for i in range(n)]
    Pm = _incidence(progs_of)
    inter = (Pm @ Pm.T).toarray()
    deg = np.asarray(Pm.sum(1)).ravel()
    union = deg[:, None] + deg[None, :] - inter
    with np.errstate(invalid="ignore", divide="ignore"):
        jacc = np.where(union > 0, inter / union, 0.0)

    def shared_courses(i: int, j: int) -> list[str]:
        return sorted({str(course_name[c]) for c in set(courses_of[i]) & set(courses_of[j])})

    Cm = _incidence([set(c) for c in courses_of])
    co = np.zeros((n, n))
    for i, j in zip(*sp.triu(Cm @ Cm.T, 1).nonzero()):     # few pairs share a course record: count distinct names only there
        co[i, j] = co[j, i] = 1.0 - 0.5 ** len(shared_courses(i, j))
    num = TW["co_teaching"] * co + TW["programmes"] * jacc + TW["content"] * np.nan_to_num(content)
    den = TW["co_teaching"] + TW["programmes"] + TW["content"] * np.isfinite(content)
    teach = num / den
    teach[~has_courses, :] = np.nan
    teach[:, ~has_courses] = np.nan
    np.fill_diagonal(teach, np.nan)

    # ---------------- field ----------------
    ssd = inp.people.ssd.astype(object).where(inp.people.ssd.notna(), None).to_numpy()
    cun = inp.people.cun.astype(object).where(inp.people.cun.notna(), None).to_numpy()
    has_field = np.array([s is not None or c is not None for s, c in zip(ssd, cun)])
    same_ssd = (ssd[:, None] == ssd[None, :]) & (ssd[:, None] != None)  # noqa: E711
    same_cun = (cun[:, None] == cun[None, :]) & (cun[:, None] != None)  # noqa: E711
    fld = np.where(same_ssd, 1.0, np.where(same_cun, 0.5, 0.0))
    fld[~has_field, :] = np.nan
    fld[:, ~has_field] = np.nan
    np.fill_diagonal(fld, np.nan)

    availability = pd.DataFrame({
        "person_id": people, "n_pubs": np.asarray(A.sum(axis=1)).ravel().astype(int), "n_pubs_embedded": n_emb,
        "n_linked_works": np.asarray(W.sum(axis=1)).ravel().astype(int), "n_courses": [len(c) for c in courses_of],
        "has_sem": eligible, "sem_confidence": person_sem_conf, "has_coupling": has_refs, "has_direct": has_works, "has_coauth": True,
        "has_teach": has_courses, "has_field": has_field,
    })

    def ev_coupling(i: int, j: int) -> list:
        excl = shared_works.get((min(i, j), max(i, j)), set())
        vi, vj = ref_vector(i, excl).toarray().ravel(), ref_vector(j, excl).toarray().ravel()
        prod = vi * vj
        top = np.argsort(-prod)[:5]
        return [{"ref": ref_ids[k], "w": round(float(prod[k]), 4)} for k in top if prod[k] > 0]

    works_of = [{work_of_pub[p] for p in pubs_of[i] if p in work_of_pub} for i in range(n)]
    work_title: dict[str, str] = {}
    for p, w in work_of_pub.items():
        work_title.setdefault(w, title_of[p])

    def ev_direct(i: int, j: int) -> list:
        excl = shared_works.get((min(i, j), max(i, j)), set())
        out = []
        for a, b in ((i, j), (j, i)):
            wb = works_of[b] - excl
            for w in sorted(works_of[a] - excl):
                cited = {ref_ids[k] for k in R[widx[w]].indices} & wb
                out += [{"citing": work_title.get(w, w), "cited": work_title.get(c, c)} for c in sorted(cited)]
        return out[:5]

    def ev_coauth(i: int, j: int) -> list:
        sh = sorted(pubs_of[i] & pubs_of[j], key=lambda p: -(year_of.get(p) or 0))
        return [{"title": title_of[p], "doi": _none(doi_of[p]), "year": _none(year_of.get(p))} for p in sh[:5]]

    def ev_teach(i: int, j: int) -> dict:
        pairs = []
        if described_of[i] and described_of[j]:
            S = E[[row_of_course[c] for c in described_of[i]]] @ E[[row_of_course[c] for c in described_of[j]]].T
            seen = set()
            for r, c in zip(*np.unravel_index(np.argsort(-S, axis=None), S.shape)):
                a, b = str(course_name[described_of[i][r]]), str(course_name[described_of[j][c]])
                if (a, b) not in seen:                       # the same course repeats every academic year
                    seen.add((a, b))
                    pairs.append({"a": a, "b": b, "cos": round(float(S[r, c]), 3)})
                if len(pairs) == 3:
                    break
        return {"shared": shared_courses(i, j), "programmes": sorted(progs_of[i] & progs_of[j]), "courses": pairs}

    def ev_field(i: int, j: int) -> dict:
        return {"ssd_i": ssd[i], "ssd_j": ssd[j], "cun_i": cun[i], "cun_j": cun[j]}

    evidence = {"sem": lambda i, j: sem_pair(i, j)[1], "coupling": ev_coupling, "direct": ev_direct,
                "coauth": ev_coauth, "teach": ev_teach, "field": ev_field}
    raw = {"sem": sem, "coupling": coupling, "direct": direct, "coauth": coauth, "teach": teach, "field": fld}
    return Result(people, raw, availability, evidence, C, eligible, sem_conf)


def _none(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
        return None
    return v.item() if hasattr(v, "item") else v


def select_edges(raw: dict[str, np.ndarray], layers: list[str], top_k: int) -> set[tuple[int, int]]:
    """Union over layers of each person's top_k neighbours with a positive, defined score."""
    pairs: set[tuple[int, int]] = set()
    for layer in layers:
        M = raw[layer]
        for i in range(M.shape[0]):
            v = M[i]
            cand = np.flatnonzero(np.isfinite(v) & (v > 0))
            for j in cand[np.argsort(-v[cand])[:top_k]]:
                pairs.add((min(i, j), max(i, j)))
    return pairs


def run(cfg: dict, args=None) -> None:
    config.ensure_dirs()
    alt = bool(getattr(args, "alt", False))
    tag = cfg.get("embedding_alt", {}).get("tag", "alt") if alt else ""
    suf = f"_{tag}" if tag else ""
    inp = load_inputs(cfg, tag=tag)
    res = compute(cfg, inp)
    P = {l: percentiles(res.raw[l]) for l in LAYERS}
    pairs = sorted(select_edges(res.raw, cfg["layers"]["edge_layers"], cfg["layers"]["top_k"]))
    people_df = inp.people
    if "affiliations" in people_df.columns:   # every structure of a person counts, not only the primary one
        aff = [{a for a in (s if isinstance(s, str) else "").split("|") if a and not a.startswith("Corso di Dottorato")}
               for s in people_df["affiliations"]]
    else:
        aff = [({d} if isinstance(d, str) else set()) for d in people_df.dept_id]
    rows = []
    for i, j in pairs:
        row = {"person_i": res.people[i], "person_j": res.people[j]}
        ev = {}
        for l in LAYERS:
            v = res.raw[l][i, j]
            row[l] = None if np.isnan(v) else float(v)
            row[f"{l}_p"] = None if np.isnan(P[l][i, j]) else float(P[l][i, j])
            if not np.isnan(v) and (v > 0 or l == "field"):
                ev[l] = res.evidence[l](i, j)
        row["sem_conf"] = None if np.isnan(res.sem_conf[i, j]) else float(res.sem_conf[i, j])
        row["unexplored"] = bool(row["coauth"] == 0 and bool(aff[i]) and bool(aff[j]) and not (aff[i] & aff[j])
                                 and max(row["sem_p"] or 0, row["coupling_p"] or 0) >= cfg["layers"]["unexplored_percentile"])
        t_ev = ev.get("teach") or {}
        row["co_teach"] = bool(t_ev.get("shared"))            # at least one course taught by both
        row["evidence"] = json.dumps(ev, ensure_ascii=False, default=_none)
        rows.append(row)
    edges = pd.DataFrame(rows)
    edges.to_parquet(config.PROCESSED / f"edges{suf}.parquet", index=False)
    res.availability.to_parquet(config.PROCESSED / f"person_layers{suf}.parquet", index=False)

    n = len(res.people)
    iu = np.triu_indices(n, 1)
    md = ["# 03 Layers\n", f"People: {n}; pairs: {len(iu[0])}; edges: {len(edges)} (top_k={cfg['layers']['top_k']} on {cfg['layers']['edge_layers']})\n",
          "| layer | people available | pairs defined | pairs NaN | edges with score |", "|---|---|---|---|---|"]
    for l in LAYERS:
        v = res.raw[l][iu]
        avail = res.availability[f"has_{l}"].mean()
        md.append(f"| {l} | {avail:.1%} | {np.isfinite(v).mean():.1%} | {np.isnan(v).mean():.1%} | {edges[l].notna().sum()} |")
    md += [f"\n`unexplored` edges: {int(edges.unexplored.sum())}"]
    (config.REPORTS / f"03_layers{suf}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("edges%s: %d; NaN rates: %s", suf, len(edges), {l: f"{np.isnan(res.raw[l][iu]).mean():.1%}" for l in LAYERS})
