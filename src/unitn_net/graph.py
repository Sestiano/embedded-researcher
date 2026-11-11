"""Step `graph`: composite graph, Leiden communities (10 seeds, stability), community names and topic terms, layout.

python-igraph: Graph.community_leiden defaults to objective_function="CPM"; "modularity" is set explicitly.
The RNG of python-igraph is Python's `random` module, so `random.seed` makes every run reproducible.
Outputs: processed/communities.parquet, processed/layout.parquet, processed/graph_meta.json, reports/03_graph.md.
"""

from __future__ import annotations

import json
import logging
import random

import igraph as ig
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from sklearn.metrics import adjusted_rand_score

from . import config
from .textnorm import norm_text
from .layers import LAYERS, composite

log = logging.getLogger(__name__)

# minimal Italian list; English comes from scikit-learn. Labels are descriptive only.
ITALIAN_STOP_WORDS = """a ad al alla alle allo agli ai anche che chi ci come con contro cui da dal dalla dalle dallo dai degli dei
del della delle dello di dove e ed è era essere fra gli i il in la le lo loro ma nel nella nelle nello negli nei non
o per più quale quali quando questa queste questi questo se si sia sono su sul sulla sulle sullo sugli sui tra un una uno
abstract analisi analysis approach approccio articolo caso casi study studio studi paper results risultati new nuovo nuova
based using use model modello models modelli data dati""".split()


def edge_composite(edges: pd.DataFrame, weights: dict[str, float], use_conf: bool = False) -> np.ndarray:
    conf = {"sem": edges["sem_conf"].astype(float).to_numpy()} if use_conf and "sem_conf" in edges else None
    return composite({l: edges[f"{l}_p"].astype(float).to_numpy() for l in LAYERS}, weights, conf)


# Words that say nothing about a topic in titles/abstracts (added to the English and Italian stop lists).
_GENERIC = frozenset("""study studies analysis approach based new case role review introduction paper results using use
effects effect model models data method methods evidence towards toward within between via role role into
studio analisi approccio nuovo nuova caso ruolo recensione introduzione risultati uso effetti modello modelli dati metodo
metodi verso tra nella nelle nello negli italia italiano italiana italiani trento trentino europa europeo
edited editor volume vol chapter capitolo ed eds part parte italy italian italians
des du les le la et de en pour dans sur sous une un aux au ou par avec sans und der die das von zu mit fur uber im dem den ein eine
el los las del al y para por con una unos sobre entre nell dell all sull dall quell dall nello negli agli
multi aware
ieee acm elsevier springer wiley copyright rights reserved ltd authors author published achieves achieve achieved existing approaches
originality methodology implications limitations participated aged years year total respectively compared overall among
state art leverage leverages leveraging leveraged propose proposed proposes present presents presented show shows shown showed
novel work works article articles contribution aim aims provide provides provided focus focuses discuss discusses discussed
investigate investigates investigated examine examines explore explores demonstrate demonstrates highlight highlights findings
suggest suggests suggested reveal reveals results conclusion conclusions background objective objectives methods purpose
significant significantly important importance different various several also however moreover thus therefore well two three
suo sua suoi sue prima dopo secondo saggio contributo articolo articoli lavoro lavori studio studi presente presenta
analizza analizzano discute discutono ciò così cioè quindi inoltre ancora mentre oltre anche
testi testo secolo secoli libro libri saggi prove""".split())

# Method phrases (statistics, study design) that say nothing about the topic. Bigrams cannot go in the stop list above:
# "mass" or "confidence" alone can be a topic (mass spectrometry), so only the phrase is dropped.
_GENERIC_PHRASES = frozenset({"confidence interval", "confidence intervals", "body mass", "real world"})


def _same_stem(a: str, b: str) -> bool:
    """Two inflections of one word (firm/firms, stimulus/stimuli, political/politics): at most 2 letters longer and sharing
    all but the last letter of the shorter. Different words with a common start (quantum/quantitative) stay apart."""
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if len(short) < 4 or len(long_) - len(short) > 2:
        return False
    common = next((k for k, (x, y) in enumerate(zip(short, long_)) if x != y), len(short))
    return common >= len(short) - 1


def community_names(members: dict[int, list[str]], people: pd.DataFrame) -> dict[int, str]:
    """Readable name from the dominant department(s): objective, unlike topic words. >= 40% share names it alone."""
    dept = dict(zip(people.person_id.astype(str), people.dept_name.fillna("")))

    def short(d: str) -> str:
        for prefix in ("Dipartimento di ", "Facoltà di "):
            d = d.removeprefix(prefix)
        return d.replace("Corso di Dottorato (D.M.226/2021) - ", "").replace("Dottorato di interesse Nazionale in ", "")

    names = {}
    for cid, ps in members.items():
        share = pd.Series([short(dept.get(p, "")) for p in ps]).replace("", np.nan).dropna().value_counts(normalize=True)
        if share.empty:
            names[cid] = ""
        elif share.iloc[0] >= 0.4 or len(share) == 1:
            names[cid] = share.index[0]
        else:
            names[cid] = " + ".join(share.index[:2])
    return names


def community_labels(members: dict[int, list[str]], pubs: pd.DataFrame, authorship: pd.DataFrame, n_terms: int,
                     min_share: float = 0.12, min_people: int = 3, exclude: frozenset = frozenset()) -> dict[int, str]:
    """Topic terms of a community: a term counts once per PERSON (not per occurrence), must be used by at least `min_share`
    of the members (and >= `min_people` of them), and is ranked by that coverage x how rare it is among all people.
    Rare words of one prolific lab (the old c-TF-IDF over the concatenated text) can no longer win."""
    pub_text = dict(zip(pubs.pub_id.astype(str), pubs.title.fillna("") + ". " + pubs.abstract.fillna("")))
    by_person = authorship.groupby(authorship.person_id.astype(str)).pub_id.apply(list).to_dict()
    persons, docs = [], []
    for person in sorted({p for ps in members.values() for p in ps}):
        texts = [pub_text[q] for q in by_person.get(person, []) if q in pub_text]
        if texts:
            persons.append(person)
            docs.append(" ".join(texts))
    if len(docs) < 2:
        return {cid: "" for cid in members}
    vec = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | set(ITALIAN_STOP_WORDS) | _GENERIC | exclude), ngram_range=(1, 2),
                          binary=True, min_df=min_people, max_features=200000, token_pattern=r"(?u)\b[^\W\d_]{3,}\b")
    X = vec.fit_transform(docs).tocsr()
    terms = np.array(vec.get_feature_names_out())
    row_of = {p: k for k, p in enumerate(persons)}
    idf = np.log((1 + X.shape[0]) / (1 + np.asarray(X.sum(axis=0)).ravel()))
    labels = {}
    for cid, ps in members.items():
        rows = [row_of[p] for p in ps if p in row_of]
        if len(rows) < 2:
            labels[cid] = ""
            continue
        cnt = np.asarray(X[rows].sum(axis=0)).ravel()
        cov = cnt / len(rows)
        score = np.where((cov >= min_share) & (cnt >= min(min_people, len(rows))), cov * idf, 0.0)
        chosen: list[str] = []
        for k in np.argsort(-score):
            if score[k] <= 0 or len(chosen) >= n_terms:
                break
            words = set(terms[k].split())
            if terms[k] in _GENERIC_PHRASES:
                continue
            if any(_same_stem(w, cw) for w in words for c in chosen for cw in c.split()):   # no variant of a chosen word
                continue
            chosen.append(terms[k])
        labels[cid] = ", ".join(chosen)
    return labels


def _partition_for_resolution(g: ig.Graph, ids: list[str], res: float, G: dict, people: pd.DataFrame,
                              pubs: pd.DataFrame, authorship: pd.DataFrame, person_names: frozenset) -> dict:
    memberships, modularity = [], []
    for seed in range(G["n_seeds"]):
        random.seed(seed)
        m = g.community_leiden(objective_function="modularity", weights="weight", resolution=res, n_iterations=-1).membership
        memberships.append(m)
        modularity.append(g.modularity(m, weights="weight"))
    aris = [adjusted_rand_score(memberships[a], memberships[b]) for a in range(len(memberships)) for b in range(a + 1, len(memberships))]
    membership = memberships[G["seed"]]
    members: dict[int, list[str]] = {}
    for p, c in zip(ids, membership):
        members.setdefault(int(c), []).append(p)
    labels = community_labels(members, pubs, authorship, G["label_terms"], exclude=person_names)
    names = community_names(members, people)
    return {
        "resolution": float(res),
        "modularity_by_seed": modularity,
        "mean_pairwise_ari": float(np.mean(aris)) if aris else 1.0,
        "membership": membership,
        "members": members,
        "labels": labels,
        "names": names,
    }


def run(cfg: dict, args=None) -> None:
    G = cfg["graph"]
    alt = bool(getattr(args, "alt", False))
    tag = cfg.get("embedding_alt", {}).get("tag", "alt") if alt else ""
    suf = f"_{tag}" if tag else ""
    people = pd.read_parquet(config.INTERIM / "people.parquet")
    edges = pd.read_parquet(config.PROCESSED / f"edges{suf}.parquet")
    pubs = pd.read_parquet(config.PROCESSED / "publications.parquet")
    authorship = pd.read_parquet(config.PROCESSED / "authorship.parquet")
    ids = people.person_id.astype(str).tolist()
    idx = {p: i for i, p in enumerate(ids)}
    w = edge_composite(edges, cfg["weights"], cfg.get("confidence", {}).get("weight_composite", False))
    keep = ~np.isnan(w)
    g = ig.Graph(n=len(ids), edges=list(zip(edges.person_i[keep].map(idx), edges.person_j[keep].map(idx))))
    g.es["weight"] = w[keep].tolist()
    log.info("graph%s: %d nodes, %d edges", suf, g.vcount(), g.ecount())

    person_names = frozenset(w for col in ("given_name", "family_name") for v in people[col].dropna()
                             for w in norm_text(v).split() if len(w) >= 3)   # first/family names are not topics
    res_list = list(dict.fromkeys([float(G["resolution"]), *[float(r) for r in G.get("resolutions", [])]]))
    parts = {str(r): _partition_for_resolution(g, ids, r, G, people, pubs, authorship, person_names) for r in res_list}
    prim = parts[str(float(G["resolution"]))]
    modularity = prim["modularity_by_seed"]
    membership = prim["membership"]
    members = prim["members"]
    labels = prim["labels"]
    names = prim["names"]
    log.info("modularity %.3f ± %.3f over %d seeds; mean pairwise ARI %.3f",
             np.mean(modularity), np.std(modularity), G["n_seeds"], prim["mean_pairwise_ari"])

    random.seed(G["seed"])
    # Layout only (not the data): intra-community edges pull harder, so communities read as separate regions.
    same = np.array([membership[a] == membership[b] for a, b in g.get_edgelist()], dtype=float)
    lw = (np.array(g.es["weight"]) * (1.0 + G.get("layout_community_pull", 4.0) * same)).tolist()
    coords = np.array(g.layout_fruchterman_reingold(weights=lw, niter=G["layout_iterations"]).coords)
    linked = np.array(g.degree()) > 0  # isolated people are pushed far away by the layout: keep them out of the scaling
    ref = coords[linked] if linked.any() else coords
    coords = np.clip((coords - ref.mean(0)) / (ref.std(0) + 1e-9), -2.5, 2.5)

    pd.DataFrame({"person_id": ids, "community_id": membership, "seed": G["seed"]}).astype(
        {"person_id": "string", "community_id": "int64", "seed": "int64"}).to_parquet(config.PROCESSED / f"communities{suf}.parquet", index=False)
    pd.DataFrame({"person_id": ids, "x": coords[:, 0], "y": coords[:, 1]}).to_parquet(config.PROCESSED / f"layout{suf}.parquet", index=False)
    partitions_out = {
        k: {
            "resolution": p["resolution"],
            "modularity": float(np.mean(p["modularity_by_seed"])),
            "ari": p["mean_pairwise_ari"],
            "membership": {pid: int(cid) for pid, cid in zip(ids, p["membership"])},
            "communities": [{"id": int(c), "label": p["labels"].get(c, ""), "name": p["names"].get(c, ""), "size": len(p["members"][c])}
                            for c in sorted(p["members"])],
        }
        for k, p in parts.items()
    }
    meta = {"n_nodes": g.vcount(), "n_edges": g.ecount(), "modularity_by_seed": modularity, "mean_pairwise_ari": prim["mean_pairwise_ari"],
            "n_communities": len(members), "labels": {str(c): l for c, l in labels.items()}, "names": {str(c): n for c, n in names.items()},
            "sizes": {str(c): len(m) for c, m in members.items()}, "weights": cfg["weights"], "resolution": G["resolution"],
            "partitions": partitions_out}
    (config.PROCESSED / f"graph_meta{suf}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")

    md = ["# 03 Graph and communities\n", f"Nodes: {g.vcount()}, edges: {g.ecount()}, composite weights: `{cfg['weights']}`",
          f"\nLeiden (modularity, resolution {G['resolution']}), {G['n_seeds']} seeds: modularity mean {np.mean(modularity):.3f} "
          f"(sd {np.std(modularity):.3f}), mean pairwise ARI {prim['mean_pairwise_ari']:.3f}; stored partition: seed {G['seed']}, "
          f"{len(members)} communities.\n", "| community | size | name (dominant department) | topic terms |", "|---|---|---|---|"]
    md += [f"| {c} | {len(members[c])} | {names[c]} | {labels[c]} |" for c in sorted(members, key=lambda c: -len(members[c]))]
    (config.REPORTS / f"03_graph{suf}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
