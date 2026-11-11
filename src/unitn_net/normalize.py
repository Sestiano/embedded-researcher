"""Step `normalize`: raw open-data JSON -> interim Parquet tables.

FIELD NAMES were checked against the 2026-09-17 snapshot (reports/00_data_audit.md): the real data uses `ruolo`,
`citazioni`, `ssd`/`cun`, list-valued `lingua` and `dipartimento`; the documented names are kept as fallbacks.
Phone numbers and any field not listed in the data model are dropped here, at ingestion.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter

import pandas as pd

from . import config, opendata
from .textnorm import extract_doi, norm_doi, norm_text, pub_id

log = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"(20\d\d)\s*[/\-–]\s*(20\d\d|\d\d)|(20\d\d)")

# candidate key names for the org-units dataset, whose schema is only loosely documented
_UNIT_ID = ("id", "idStruttura", "codice")
_UNIT_NAME = ("nome", "nomeStruttura", "denominazione", "descrizione")
_UNIT_PARENT = ("idPadre", "idStrutturaPadre", "parent", "padre", "idParent")


def _first(r: dict, *keys: str):
    for k in keys:
        if r.get(k) not in (None, ""):
            return r[k]
    return None


def _str(v) -> str | None:
    return None if v in (None, "") else str(v).strip()


def _structure_rank(name: str | None) -> int:
    """Which of a person's structures is shown as THE department: a real department beats a school, a centre, a doctoral programme."""
    n = (name or "").lower()
    for rank, prefix in enumerate(("dipartimento", "facolt", "scuola", "centro", "corso di dottorato")):
        if n.startswith(prefix):
            return rank
    return 5


def people_table(recs: list[dict], roles: list[str]) -> pd.DataFrame:
    roles = [r.lower() for r in roles]
    rows = []
    for r in recs:
        matching = [p for p in (r.get("posizioni") or []) if isinstance(p, dict)
                    and any(role in (_first(p, "ruolo", "descrizioneRuolo") or "").lower() for role in roles)]
        if not matching or r.get("id") in (None, ""):
            continue
        # Primary structure: best-ranked kind, ties -> first listed. ALL structures are kept in `affiliations`
        # (a CIMEC member is often listed under a department first; taking only the first hid the centre).
        p = min(enumerate(matching), key=lambda ip: (_structure_rank(ip[1].get("nomeStruttura")), ip[0]))[1]
        affiliations = list(dict.fromkeys(a for a in (_str(q.get("nomeStruttura")) for q in matching) if a))
        rows.append({
            "person_id": str(r["id"]), "given_name": _str(r.get("nome")), "family_name": _str(r.get("cognome")),
            "role": _str(_first(p, "ruolo", "descrizioneRuolo")), "dept_id": _str(p.get("idStruttura")),
            "dept_name": _str(p.get("nomeStruttura")), "ssd": _str(_first(r, "SSD", "ssd")),
            "cun": _str(_first(r, "CUN", "cun")), "affiliations": "|".join(affiliations),
        })
    df = pd.DataFrame(rows, columns=["person_id", "given_name", "family_name", "role", "dept_id", "dept_name", "ssd", "cun", "affiliations"])
    dup = df.person_id.duplicated().sum()
    if dup:
        log.warning("%d duplicated person ids in staff data; keeping the first", dup)
    return df.drop_duplicates("person_id").astype("string").reset_index(drop=True)


MANUAL_AFFILIATIONS = "manual_affiliations.csv"   # data/manual_affiliations.csv: given_name,family_name,structure (one row per structure)
OPTOUT = "optout.csv"                             # data/optout.csv: person_id (or given_name,family_name) of people to exclude


def apply_optout(people: pd.DataFrame, path) -> pd.DataFrame:
    """Exclude the people listed in `data/optout.csv` (local, never in git). Columns: `person_id`, or `given_name,family_name`
    (one row per person). A row that matches nobody, or a name shared by two people, is logged and never guessed: an exclusion
    request must not fail silently."""
    if not path.exists():
        return people
    opt = pd.read_csv(path, dtype=str).fillna("")
    key = lambda f, g: f"{norm_text(f)}|{norm_text(g)}"   # noqa: E731
    by_name: dict[str, list[str]] = {}
    for pid, f, g in zip(people.person_id, people.family_name, people.given_name):
        by_name.setdefault(key(f, g), []).append(str(pid))
    known = set(people.person_id.astype(str))
    drop: set[str] = set()
    for r in opt.to_dict("records"):
        pid = r.get("person_id", "").strip()
        if pid:
            if pid in known:
                drop.add(pid)
            else:
                log.warning("opt-out: person_id %s not found among the people in scope", pid)
            continue
        hits = by_name.get(key(r.get("family_name", ""), r.get("given_name", "")), [])
        if len(hits) == 1:
            drop.add(hits[0])
        else:
            log.warning("opt-out NOT applied (%d matches, use person_id): %s %s", len(hits), r.get("given_name", ""), r.get("family_name", ""))
    log.info("opt-out: %d people excluded (%s)", len(drop), path)
    return people[~people.person_id.isin(drop)].reset_index(drop=True)


def apply_manual_affiliations(people: pd.DataFrame, path) -> pd.DataFrame:
    """Add structures the open data does not list (e.g. someone known to belong to a centre). Matched on normalised
    family + given name; a name shared by two in-scope people is skipped and logged, never guessed. Local file, never exported
    as such. A person may appear on several rows."""
    if not path.exists():
        return people
    manual = pd.read_csv(path, dtype=str).fillna("")
    key = lambda f, g: f"{norm_text(f)}|{norm_text(g)}"   # noqa: E731
    idx: dict[str, list[int]] = {}
    for i, (f, g) in enumerate(zip(people.family_name, people.given_name)):
        idx.setdefault(key(f, g), []).append(i)
    people = people.copy()
    added = 0
    for r in manual.itertuples():
        hits = idx.get(key(r.family_name, r.given_name), [])
        if len(hits) != 1 or not r.structure.strip():
            log.warning("manual affiliation not applied (%d matches): %s %s -> %s", len(hits), r.given_name, r.family_name, r.structure)
            continue
        cur = [a for a in (people.at[hits[0], "affiliations"] or "").split("|") if a]
        if r.structure.strip() not in cur:
            people.at[hits[0], "affiliations"] = "|".join(cur + [r.structure.strip()])
            added += 1
    log.info("manual affiliations: %d added from %s", added, path)
    return people


def org_units_table(recs: list[dict]) -> pd.DataFrame:
    rows = [{"unit_id": _str(_first(r, *_UNIT_ID)), "name": _str(_first(r, *_UNIT_NAME)),
             "parent_id": _str(_first(r, *_UNIT_PARENT))} for r in recs]
    df = pd.DataFrame(rows, columns=["unit_id", "name", "parent_id"]).astype("string")
    if df.unit_id.isna().all():
        log.warning("org units: no id field among %s; check reports/00_data_audit.md", _UNIT_ID)
    return df


def publications_tables(resources: list[tuple[dict, list[dict]]], year_min: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    pubs: dict[str, dict] = {}
    authors: dict[str, set[str]] = {}
    stats = Counter()
    for _, recs in resources:
        for r in recs:
            anno = r.get("anno")
            year = int(anno) if anno not in (None, "") and str(anno).lstrip("-").isdigit() else None
            in_press = year == 9999
            if in_press:
                year = None
            if year is not None and year < year_min:
                stats["skipped_before_year_min"] += 1
                continue
            title = _str(r.get("titolo"))
            if not title:
                stats["skipped_no_title"] += 1
                continue
            citation = _str(_first(r, "citazione", "citazioni"))
            pid = pub_id(title, year, citation)
            ids = {str(a["id"]) for a in (r.get("autori") or []) if isinstance(a, dict) and a.get("id") not in (None, "")}
            if pid in pubs:
                stats["duplicates"] += 1
                authors[pid] |= ids
                continue
            doi, doi_source = norm_doi(_first(r, "doi", "DOI")), "field"
            if doi is None:
                doi, doi_source = extract_doi(citation), "citation_regex"
            if doi is None:
                doi_source = None
            pubs[pid] = {"pub_id": pid, "type": _str(r.get("tipo")), "title": title,
                         "abstract": _str(r.get("abstract")), "language": _str(", ".join(r["lingua"]) if isinstance(r.get("lingua"), list) else r.get("lingua")),
                         "year": year, "in_press": in_press, "doi": doi, "doi_source": doi_source,
                         "citation_text": citation}
            authors[pid] = ids
    stats["publications"] = len(pubs)
    df = pd.DataFrame(list(pubs.values()), columns=["pub_id", "type", "title", "abstract", "language", "year", "in_press",
                                                    "doi", "doi_source", "citation_text"])
    df = df.astype({"pub_id": "string", "type": "string", "title": "string", "abstract": "string", "language": "string",
                    "year": "Int64", "in_press": "boolean", "doi": "string", "doi_source": "string", "citation_text": "string"})
    auth = pd.DataFrame([(p, a) for p, ids in authors.items() for a in sorted(ids)], columns=["pub_id", "person_id"]).astype("string")
    return df, auth, dict(stats)


def academic_year(res: dict) -> str:
    m = _YEAR_RE.search(f"{res.get('name') or ''} {res.get('description') or ''}")
    if not m:
        return "unknown"
    if m.group(1):
        end = m.group(2)
        return f"{m.group(1)}/{end if len(end) == 4 else m.group(1)[:2] + end}"
    return m.group(3)


def courses_tables(resources: list[tuple[dict, list[dict]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    courses: dict[str, dict] = {}
    teaching: set[tuple[str, str, str]] = set()
    for res, recs in resources:
        ay = academic_year(res)
        for r in recs:
            name = _str(r.get("nome"))
            if not name:
                continue
            dept = r.get("dipartimento")
            if isinstance(dept, list):  # real data: a list of {nome, id}; the first one is used
                dept = dept[0] if dept else {}
            dept = dept if isinstance(dept, dict) else {}
            programme = _str(r.get("corsoStudi"))
            dept_id = _str(dept.get("id"))
            cid = hashlib.sha1(f"{ay}|{norm_text(name)}|{norm_text(programme)}|{dept_id or ''}".encode()).hexdigest()
            courses.setdefault(cid, {"course_id": cid, "academic_year": ay, "name": name,
                                     "description": _str(r.get("descrizione")), "degree_programme": programme,
                                     "dept_id": dept_id, "dept_name": _str(dept.get("nome"))})
            for key, role in (("docenti", "docente"), ("assistenti", "assistente")):
                for d in r.get(key) or []:
                    if isinstance(d, dict) and d.get("id") not in (None, ""):
                        teaching.add((cid, str(d["id"]), role))
    cdf = pd.DataFrame(list(courses.values()), columns=["course_id", "academic_year", "name", "description",
                                                        "degree_programme", "dept_id", "dept_name"]).astype("string")
    tdf = pd.DataFrame(sorted(teaching), columns=["course_id", "person_id", "teaching_role"]).astype("string")
    return cdf, tdf


def run(cfg: dict, args=None) -> None:
    config.ensure_dirs()
    raw = config.latest_raw("opendata")
    stats: dict = {"raw_snapshot": raw.name}

    people = people_table([r for _, rs in opendata.load_resources(raw, opendata.STAFF) for r in rs], cfg["scope"]["roles"])
    people = apply_optout(people, config.DATA / OPTOUT)
    people = apply_manual_affiliations(people, config.DATA / MANUAL_AFFILIATIONS)
    stats["people"] = len(people)
    log.info("people in scope: %d", len(people))

    units = org_units_table([r for _, rs in opendata.load_resources(raw, opendata.UNITS) for r in rs])
    pubs, auth, pstats = publications_tables(opendata.load_resources(raw, opendata.PUBS), cfg["scope"]["pub_year_min"])
    stats.update(pstats)
    stats["authorship_rows"] = len(auth)
    stats["authorship_rows_in_scope"] = int(auth.person_id.isin(people.person_id).sum())
    log.info("publications: %d (%d duplicates across yearly files), doi: %s",
             len(pubs), pstats.get("duplicates", 0), pubs.doi_source.value_counts(dropna=False).to_dict())

    courses, teaching = courses_tables(opendata.load_resources(raw, opendata.COURSES))
    stats["courses"] = len(courses)
    stats["courses_by_year"] = courses.academic_year.value_counts().to_dict()
    stats["teaching_rows_in_scope"] = int(teaching.person_id.isin(people.person_id).sum())
    log.info("courses: %d, academic years: %s", len(courses), stats["courses_by_year"])

    for name, df in [("people", people), ("org_units", units), ("publications", pubs), ("authorship", auth),
                     ("courses", courses), ("teaching", teaching)]:
        df.to_parquet(config.INTERIM / f"{name}.parquet", index=False)
    (config.INTERIM / "normalize_stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    log.info("wrote interim tables to %s", config.INTERIM)
