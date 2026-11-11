"""Step `fetch-openalex`: OpenAlex — institution works cache (citations, fallback abstracts) and DOI lookups.

Optional: without `OPENALEX_API_KEY` the step exits cleanly and the layers `coupling`/`direct` stay NaN.
Docs: https://docs.openalex.org/ — filtering https://help.openalex.org/api/filtering/,
costs https://help.openalex.org/access/example-costs/ (list+filter $0.10 / 1,000 calls; singleton by DOI free).
Authentication is passed as the `api_key` query parameter: verify this against the current docs before the
first run (the key form was not verified when this was written).
Every response `meta` is logged (cost accounting). Raw pages are immutable under data/raw/openalex/<date>/.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import math
import os
import time
from pathlib import Path

import pandas as pd

from . import config, net
from .textnorm import norm_doi

log = logging.getLogger(__name__)

FIELDS = "id,doi,title,publication_year,language,authorships,referenced_works,cited_by_count,abstract_inverted_index,topics"


def reconstruct_abstract(inv: dict | None) -> str | None:
    """OpenAlex stores abstracts as {word: [positions]}; rebuild the word sequence."""
    if not inv:
        return None
    words = sorted((pos, w) for w, positions in inv.items() for pos in positions)
    return " ".join(w for _, w in words) or None


def _get(s, cfg: dict, key: str, path: str, params: dict) -> dict:
    data = net.get_json(s, cfg["openalex"]["base_url"] + path, {**params, "api_key": key})
    if "meta" in data:
        log.debug("meta: %s", data["meta"])
    return data


def fetch_institution_works(s, cfg: dict, key: str, out: Path) -> None:
    oa = cfg["openalex"]
    inst = _get(s, cfg, key, f"/institutions/{oa['institution_id']}", {})
    log.info("institution %s = %s (ROR %s, works_count %s)", oa["institution_id"], inst.get("display_name"),
             inst.get("ror"), inst.get("works_count"))
    (out / "institution.json").write_text(json.dumps(inst, ensure_ascii=False, indent=1), encoding="utf-8")

    flt = f"institutions.id:{oa['institution_id']},publication_year:>{cfg['scope']['pub_year_min'] - 1}"
    first = _get(s, cfg, key, "/works", {"filter": flt, "per_page": 1, "select": "id"})
    count = first["meta"]["count"]
    calls = math.ceil(count / oa["per_page"])
    cost = calls / 1000 * oa["list_cost_per_1000"]
    log.info("works matching %s: %d -> %d list calls -> ~$%.3f (meta: %s)", flt, count, calls, cost, first["meta"])
    if cost > oa["max_cost_usd"]:
        raise SystemExit(f"STOP: estimated cost ${cost:.3f} exceeds openalex.max_cost_usd={oa['max_cost_usd']}")

    progress_path = out / "works_progress.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {"page": 0, "cursor": "*", "complete": False, "n_calls": 0}
    if progress["complete"]:
        log.info("institution works already downloaded in %s", out)
        return
    while progress["cursor"]:
        data = _get(s, cfg, key, "/works", {"filter": flt, "per_page": oa["per_page"], "cursor": progress["cursor"], "select": FIELDS})
        (out / f"works_{progress['page']:05d}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        progress.update(page=progress["page"] + 1, cursor=data["meta"].get("next_cursor"), n_calls=progress["n_calls"] + 1)
        if not data["results"]:
            progress["cursor"] = None
        progress["complete"] = not progress["cursor"]
        progress_path.write_text(json.dumps(progress))
        if progress["page"] % 20 == 0:
            log.info("page %d / ~%d", progress["page"], calls)
    log.info("institution works: %d pages, %d list calls (~$%.3f)", progress["page"], progress["n_calls"],
             progress["n_calls"] / 1000 * oa["list_cost_per_1000"])


def fetch_by_doi(s, cfg: dict, key: str, out: Path, dois: list[str]) -> None:
    """Singleton lookups (free tier) for DOIs of open-data publications absent from the institution cache."""
    d = out / "by_doi"
    d.mkdir(exist_ok=True)
    todo = [x for x in dois if not (d / f"{hashlib.sha1(x.encode()).hexdigest()}.json").exists()]
    log.info("DOI lookups: %d to do (%d cached)", len(todo), len(dois) - len(todo))
    for n, doi in enumerate(todo, 1):
        path = d / f"{hashlib.sha1(doi.encode()).hexdigest()}.json"
        r = s.get(f"{cfg['openalex']['base_url']}/works/https://doi.org/{doi}", params={"api_key": key}, timeout=net.TIMEOUT)
        if r.status_code == 404:
            path.write_text(json.dumps({"doi": doi, "not_found": True}))
        else:
            r.raise_for_status()
            path.write_text(r.text, encoding="utf-8")
        if n % 200 == 0:
            log.info("DOI lookups: %d / %d", n, len(todo))
        time.sleep(0.1)


def _work_row(w: dict) -> dict:
    topics = w.get("topics") or []
    return {
        "openalex_id": w["id"].rsplit("/", 1)[-1], "doi": norm_doi(w.get("doi")), "title": w.get("title"),
        "year": w.get("publication_year"), "language": w.get("language"),
        "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
        "cited_by_count": w.get("cited_by_count"),
        "author_names": [a.get("author", {}).get("display_name") or "" for a in w.get("authorships") or []],
        "primary_topic": topics[0].get("display_name") if topics else None,
        "n_references": len(w.get("referenced_works") or []),
    }


def build_tables(out: Path) -> None:
    """Raw pages + DOI lookups -> interim/openalex_works.parquet and interim/oa_references.parquet."""
    works: dict[str, dict] = {}
    for page in sorted(out.glob("works_*.json")):
        for w in json.loads(page.read_text(encoding="utf-8"))["results"]:
            works.setdefault(w["id"], w)
    for f in (out / "by_doi").glob("*.json") if (out / "by_doi").exists() else []:
        w = json.loads(f.read_text(encoding="utf-8"))
        if not w.get("not_found"):
            works.setdefault(w["id"], w)
    rows = [_work_row(w) for w in works.values()]
    df = pd.DataFrame(rows, columns=list(_work_row({"id": "W0"}).keys()))
    df = df.astype({"openalex_id": "string", "doi": "string", "title": "string", "year": "Int64", "language": "string",
                    "abstract": "string", "cited_by_count": "Int64", "primary_topic": "string", "n_references": "Int64"})
    refs = pd.DataFrame([(w["id"].rsplit("/", 1)[-1], r.rsplit("/", 1)[-1]) for w in works.values()
                         for r in w.get("referenced_works") or []], columns=["openalex_id", "referenced_openalex_id"]).astype("string")
    df.to_parquet(config.INTERIM / "openalex_works.parquet", index=False)
    refs.to_parquet(config.INTERIM / "oa_references.parquet", index=False)
    log.info("OpenAlex works: %d (with abstract %d, with DOI %d); references: %d",
             len(df), df.abstract.notna().sum(), df.doi.notna().sum(), len(refs))


def _dois_to_lookup(out: Path) -> list[str]:
    from .link import iris_dois_for_publications  # local import: link depends on pandas only
    pubs = pd.read_parquet(config.INTERIM / "publications.parquet")
    iris_path = config.INTERIM / "iris_records.parquet"
    dois = set(pubs.doi.dropna())
    if iris_path.exists():
        dois |= set(iris_dois_for_publications(pubs, pd.read_parquet(iris_path)).dropna())
    cached = set()
    for page in out.glob("works_*.json"):
        cached |= {norm_doi(w.get("doi")) for w in json.loads(page.read_text(encoding="utf-8"))["results"]}
    return sorted(dois - cached)


def run(cfg: dict, args=None) -> None:
    config.ensure_dirs()
    key = os.environ.get(cfg["openalex"]["api_key_env"])
    if not key:
        log.warning("%s not set: skipping OpenAlex; layers coupling/direct will be NaN", cfg["openalex"]["api_key_env"])
        return
    base = config.RAW / "openalex"
    existing = sorted(p for p in base.glob("*") if p.is_dir()) if base.exists() else []
    out = existing[-1] if existing else base / dt.date.today().isoformat()  # one snapshot; delete the folder to refresh
    out.mkdir(parents=True, exist_ok=True)
    s = net.session(cfg)
    fetch_institution_works(s, cfg, key, out)
    fetch_by_doi(s, cfg, key, out, _dois_to_lookup(out))
    build_tables(out)
