"""Step `link`: link open-data publications to OpenAlex works and settle abstracts.

Order, recorded in `link_method`:
1. `doi`   — the publication has a DOI (field, regex on `citazione`, or recovered from IRIS by exact
             normalised title + year; `doi_source` says which) and that DOI is in the OpenAlex tables.
2. `title` — normalised title similarity >= link.title_threshold, |year diff| <= 1, >= 1 UniTrento family
             name among the work's authors, >= link.min_title_tokens tokens; ambiguous candidates are logged.
3. `none`.
Abstract: open-data field first, then IRIS (`fetch-iris`, matched by DOI or exact title+year, same language only), OpenAlex reconstruction as fallback, else none.
Outputs: processed/publications.parquet, processed/authorship.parquet, processed/oa_references.parquet,
reports/01_linking.md and reports/01_title_match_sample.csv (50 rows for the manual precision check).
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from . import config
from .textnorm import detect_lang, norm_doi, norm_text, text_lang

log = logging.getLogger(__name__)


def iris_dois_for_publications(pubs: pd.DataFrame, iris: pd.DataFrame) -> pd.Series:
    """pub_id -> DOI for publications without DOI whose normalised title matches exactly one IRIS DOI (|year diff| <= 1)."""
    iris = iris.dropna(subset=["doi", "title"])
    index: dict[str, list[tuple[object, str]]] = {}
    for title, year, doi in zip(iris.title, iris.year, iris.doi):
        index.setdefault(norm_text(title), []).append((year, doi))
    found, ambiguous = {}, 0
    for pid, title, year, doi in zip(pubs.pub_id, pubs.title, pubs.year, pubs.doi):
        if pd.notna(doi):
            continue
        cands = index.get(norm_text(title), [])
        dois = {d for y, d in cands if pd.isna(year) or pd.isna(y) or abs(int(y) - int(year)) <= 1}
        if len(dois) == 1:
            found[pid] = dois.pop()
        elif len(dois) > 1:
            ambiguous += 1
    log.info("IRIS: DOI recovered for %d publications (%d ambiguous titles skipped)", len(found), ambiguous)
    return pd.Series(found, dtype="string", name="doi")


def iris_abstracts_for_publications(pubs: pd.DataFrame, iris: pd.DataFrame) -> pd.DataFrame:
    """pub_id -> IRIS abstract, in the publication's own language (within-language embeddings).

    Match: DOI first, then exact normalised title with |year diff| <= 1 (only when unique). A record may carry two
    descriptions (abstract_alt); the one whose detected language equals the publication's language wins, an undecided one
    is accepted, one in another language is dropped and counted (`wrong_lang`). Returns pub_id, abstract, iris_id."""
    iris = iris[iris.abstract.notna() | iris.abstract_alt.notna()].copy()
    by_doi = {}
    for k, d in enumerate(iris.doi):
        nd = norm_doi(d) if pd.notna(d) else None
        if nd:
            by_doi.setdefault(nd, []).append(k)
    by_title: dict[str, list[int]] = {}
    for k, t in enumerate(iris.title):
        by_title.setdefault(norm_text(t), []).append(k)
    rec = iris.reset_index(drop=True)
    rows, ambiguous, wrong_lang = [], 0, 0
    for pid, title, year, doi, declared in zip(pubs.pub_id, pubs.title, pubs.year, pubs.doi, pubs.language):
        nd = norm_doi(doi) if pd.notna(doi) else None
        ks = by_doi.get(nd, []) if nd else []
        if not ks:
            ks = [k for k in by_title.get(norm_text(title), [])
                  if pd.isna(year) or pd.isna(rec.year[k]) or abs(int(rec.year[k]) - int(year)) <= 1]
        if not ks:
            continue
        if len(ks) > 1:
            ambiguous += 1
            continue
        r = rec.iloc[ks[0]]
        target = text_lang(title, None, declared)
        chosen = None
        for cand in (r.abstract, r.abstract_alt):
            if pd.isna(cand) or not str(cand).strip():
                continue
            lang = detect_lang(cand)
            if lang is None or target == "other" or lang == target:
                chosen = cand
                break
        if chosen is None:
            wrong_lang += 1
            continue
        rows.append({"pub_id": pid, "abstract": chosen, "iris_id": r.iris_id})
    log.info("IRIS abstracts: %d publications, %d ambiguous skipped, %d only in another language", len(rows), ambiguous, wrong_lang)
    return pd.DataFrame(rows, columns=["pub_id", "abstract", "iris_id"])


def title_match(pubs: pd.DataFrame, oa: pd.DataFrame, family_names: dict[str, set[str]], cfg: dict) -> pd.DataFrame:
    """Fuzzy title matching against the OpenAlex cache. Candidate retrieval: char 3-gram TF-IDF cosine;
    acceptance: difflib ratio >= threshold + year and author checks. Returns pub_id, openalex_id, similarity."""
    L = cfg["link"]
    pubs = pubs[pubs.title.map(lambda t: len(norm_text(t).split()) >= L["min_title_tokens"])]
    oa = oa.dropna(subset=["title"]).reset_index(drop=True)
    if pubs.empty or oa.empty:
        return pd.DataFrame(columns=["pub_id", "openalex_id", "similarity"])
    oa_titles = oa.title.map(norm_text).tolist()
    oa_years = oa.year.astype(float).to_numpy()
    oa_authors = [" ".join(norm_text(a) for a in names) for names in oa.author_names]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 3)).fit(oa_titles)
    X_oa = vec.transform(oa_titles)
    rows, ambiguous, rejected = [], 0, {"year": 0, "author": 0, "ratio": 0}
    p_titles = pubs.title.map(norm_text).tolist()
    p_years = pubs.year.astype(float).to_numpy()
    p_ids = pubs.pub_id.tolist()
    for start in range(0, len(pubs), 200):
        sims = (vec.transform(p_titles[start:start + 200]) @ X_oa.T).toarray()
        for k, sim in enumerate(sims):
            i = start + k
            if not np.isnan(p_years[i]):
                sim = np.where(np.abs(oa_years - p_years[i]) <= 1, sim, -1.0)
            top2 = np.argpartition(-sim, 1)[:2] if len(sim) > 1 else np.array([0])
            top2 = top2[np.argsort(-sim[top2])]
            best = top2[0]
            if sim[best] <= 0:
                rejected["year"] += 1
                continue
            if len(top2) > 1 and sim[top2[1]] >= sim[best] - L["ambiguity_margin"] and oa_titles[top2[1]] != oa_titles[best]:
                ambiguous += 1
                log.debug("ambiguous: %r ~ %r / %r", p_titles[i], oa_titles[best], oa_titles[top2[1]])
                continue
            ratio = SequenceMatcher(None, p_titles[i], oa_titles[best]).ratio()
            if ratio < L["title_threshold"]:
                rejected["ratio"] += 1
                continue
            names = {n for n in family_names.get(p_ids[i], set()) if len(n) >= 3}
            if not any(f" {n} " in f" {oa_authors[best]} " for n in names):
                rejected["author"] += 1
                continue
            rows.append({"pub_id": p_ids[i], "openalex_id": oa.openalex_id.iloc[best], "similarity": ratio})
    log.info("title match: %d linked, %d ambiguous, rejected %s", len(rows), ambiguous, rejected)
    return pd.DataFrame(rows, columns=["pub_id", "openalex_id", "similarity"])


def _md_counts(s: pd.Series, title: str) -> list[str]:
    c = s.value_counts(dropna=False)
    return [f"\n### {title}\n"] + [f"- `{k}`: {v} ({v / len(s):.1%})" for k, v in c.items()]


def run(cfg: dict, args=None) -> None:
    config.ensure_dirs()
    pubs = pd.read_parquet(config.INTERIM / "publications.parquet")
    auth = pd.read_parquet(config.INTERIM / "authorship.parquet")
    people = pd.read_parquet(config.INTERIM / "people.parquet")
    iris_path, oa_path = config.INTERIM / "iris_records.parquet", config.INTERIM / "openalex_works.parquet"
    iris = pd.read_parquet(iris_path) if iris_path.exists() else None
    oa = pd.read_parquet(oa_path) if oa_path.exists() else pd.DataFrame(columns=["openalex_id", "doi", "title", "year", "abstract", "author_names"])
    refs = pd.read_parquet(config.INTERIM / "oa_references.parquet") if oa_path.exists() else pd.DataFrame(columns=["openalex_id", "referenced_openalex_id"])
    if iris is None:
        log.warning("no IRIS records: DOI recovery via IRIS skipped")
    if oa.empty:
        log.warning("no OpenAlex tables: no work links, no fallback abstracts")

    if iris is not None:
        recovered = iris_dois_for_publications(pubs, iris)
        m = pubs.doi.isna() & pubs.pub_id.isin(recovered.index)
        pubs.loc[m, "doi"] = pubs.loc[m, "pub_id"].map(recovered)
        pubs.loc[m, "doi_source"] = "iris"

    doi_map = dict(zip(oa.doi.dropna(), oa.openalex_id[oa.doi.notna()]))
    pubs["openalex_id"] = pubs.doi.map(doi_map).astype("string")
    pubs["link_method"] = pd.Series(np.where(pubs.openalex_id.notna(), "doi", None), index=pubs.index, dtype="string")

    sample = pd.DataFrame()
    if not oa.empty:
        fam = auth.merge(people[["person_id", "family_name"]], on="person_id")
        family_names = fam.groupby("pub_id").family_name.apply(lambda s: {norm_text(x) for x in s}).to_dict()
        tm = title_match(pubs[pubs.openalex_id.isna()], oa, family_names, cfg)
        if not tm.empty:
            tm = tm.set_index("pub_id")
            m = pubs.pub_id.isin(tm.index)
            pubs.loc[m, "openalex_id"] = pubs.loc[m, "pub_id"].map(tm.openalex_id)
            pubs.loc[m, "link_method"] = "title"
            sample = tm.sample(min(50, len(tm)), random_state=0).reset_index()
            sample = sample.merge(pubs[["pub_id", "title", "year"]], on="pub_id") \
                .merge(oa[["openalex_id", "title", "year"]].rename(columns={"title": "oa_title", "year": "oa_year"}), on="openalex_id")
            sample["correct"] = ""
    pubs["link_method"] = pubs.link_method.fillna("none")

    from_opendata = pubs.abstract.notna().to_numpy()
    if iris is not None and "abstract" in iris.columns:
        ia = iris_abstracts_for_publications(pubs, iris).set_index("pub_id")
        m = pubs.abstract.isna() & pubs.pub_id.isin(ia.index)
        pubs.loc[m, "abstract"] = pubs.loc[m, "pub_id"].map(ia.abstract)
    oa_abs = dict(zip(oa.openalex_id, oa.abstract)) if not oa.empty else {}
    fallback = pubs.openalex_id.map(oa_abs).astype("string")
    pubs["abstract_source"] = pd.Series(np.where(from_opendata, "opendata", np.where(pubs.abstract.notna(), "iris",
                                                 np.where(fallback.notna(), "openalex", "none"))), index=pubs.index, dtype="string")
    pubs["abstract"] = pubs.abstract.fillna(fallback)
    pubs["abstract_lang"] = pubs.language
    pubs["text_lang"] = [text_lang(t, a, d) for t, a, d in zip(pubs.title, pubs.abstract, pubs.language)]

    cols = ["pub_id", "type", "title", "abstract", "abstract_source", "abstract_lang", "year", "in_press", "doi", "doi_source",
            "openalex_id", "link_method", "citation_text", "text_lang"]
    pubs[cols].to_parquet(config.PROCESSED / "publications.parquet", index=False)
    auth[auth.pub_id.isin(pubs.pub_id) & auth.person_id.isin(people.person_id)].to_parquet(config.PROCESSED / "authorship.parquet", index=False)
    refs[refs.openalex_id.isin(pubs.openalex_id.dropna())].to_parquet(config.PROCESSED / "oa_references.parquet", index=False)

    md = ["# 01 Linking\n", f"Publications: {len(pubs)}"]
    md += _md_counts(pubs.doi_source, "DOI source")
    md += _md_counts(pubs.link_method, "Link method")
    md += _md_counts(pubs.abstract_source, "Abstract source")
    md += _md_counts(pubs.text_lang, "Language of the embedded text")
    cov = pubs.groupby("text_lang").abstract.apply(lambda s: s.notna().mean())
    md += ["\n### Abstract coverage by language\n"] + [f"- `{k}`: {v:.1%}" for k, v in cov.items()]
    md += ["\n## Manual precision check\n",
           f"`reports/01_title_match_sample.csv`: {len(sample)} random title matches; fill `correct` (1/0). "
           "Precision must be >= 0.95, otherwise STOP and raise `link.title_threshold`."]
    (config.REPORTS / "01_linking.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sample.to_csv(config.REPORTS / "01_title_match_sample.csv", index=False)
    log.info("link methods: %s", pubs.link_method.value_counts().to_dict())
