"""Step `fetch-iris`: harvest IRIS via OAI-PMH for the abstracts (and the DOIs missing from the open data).

OAI-PMH 2.0: https://www.openarchives.org/OAI/openarchivesprotocol.html
- `Identify` and `ListMetadataFormats` are saved first: inspect them, then confirm `iris.metadata_prefix`.
- `ListRecords` pages are stored verbatim (data/raw/iris/<date>/page_NNNNN.xml), resumptionToken honoured,
  >= `iris.min_interval_s` between requests. The harvest resumes from `progress.json` if interrupted.
- Parsing is namespace-agnostic (local element names only); the layout was checked on the first page on 2026-09-29.
- `dc:description` holds the abstracts used by `link` and `embed`.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from . import config, net
from .textnorm import DOI_RE, norm_doi

log = logging.getLogger(__name__)
OAI = "{http://www.openarchives.org/OAI/2.0/}"
_HANDLE_RE = re.compile(r"(?:hdl\.handle\.net/|^)(\d{4,6}/\d+)")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _get_xml(s, url: str, params: dict) -> tuple[ET.Element, bytes]:
    r = s.get(url, params=params, timeout=net.TIMEOUT)
    r.raise_for_status()
    return ET.fromstring(r.content), r.content


def harvest(cfg: dict, out: Path) -> None:
    s = net.session(cfg)
    ep, prefix, pause = cfg["iris"]["endpoint"], cfg["iris"]["metadata_prefix"], cfg["iris"]["min_interval_s"]
    for verb in ("Identify", "ListMetadataFormats"):
        if not (out / f"{verb}.xml").exists():
            _, raw = _get_xml(s, ep, {"verb": verb})
            (out / f"{verb}.xml").write_bytes(raw)
            time.sleep(pause)
    progress_path = out / "progress.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {"page": 0, "token": None, "complete": False}
    if progress["complete"]:
        log.info("harvest already complete in %s", out)
        return
    while True:
        params = {"verb": "ListRecords", "resumptionToken": progress["token"]} if progress["token"] \
            else {"verb": "ListRecords", "metadataPrefix": prefix}
        root, raw = _get_xml(s, ep, params)
        err = root.find(f"{OAI}error")
        if err is not None:
            raise RuntimeError(f"OAI-PMH error {err.get('code')}: {err.text}")
        (out / f"page_{progress['page']:05d}.xml").write_bytes(raw)
        tok = root.find(f".//{OAI}resumptionToken")
        progress["page"] += 1
        progress["token"] = (tok.text or "").strip() if tok is not None else None
        if progress["page"] % 50 == 0:
            log.info("page %d (completeListSize=%s)", progress["page"], tok.get("completeListSize") if tok is not None else "?")
        if not progress["token"]:
            progress["complete"] = True
        progress_path.write_text(json.dumps(progress))
        if progress["complete"]:
            break
        time.sleep(pause)
    log.info("harvested %d pages", progress["page"])


IRIS_OWN_DOI_PREFIX = "10.15168/"   # DOIs minted by IRIS itself for the handle: not the publisher's DOI


def _parse_record(rec: ET.Element) -> dict | None:
    """oai_openaire layout (verified 2026-09-29): datacite `titles/title`, `dates/date[@dateType=Issued]`,
    `alternateIdentifiers/alternateIdentifier`, `dc:description` (the abstract; up to two per record, no xml:lang)."""
    header = rec.find(f"{OAI}header")
    if header is None or header.get("status") == "deleted":
        return None
    ident = header.findtext(f"{OAI}identifier")
    meta = rec.find(f"{OAI}metadata")
    if meta is None:
        return None
    title, year, doi, handle, lang = None, None, None, None, None
    descriptions: list[str] = []
    for el in meta.iter():
        name, text = _local(el.tag), (el.text or "").strip()
        if not text:
            continue
        if name == "title" and title is None:
            title = text
        elif name == "alternateIdentifier":
            m = DOI_RE.search(text)
            d = norm_doi(m.group(0)) if m else None
            if doi is None and d and not d.startswith(IRIS_OWN_DOI_PREFIX):
                doi = d
            if handle is None and "hdl.handle.net" in text:
                h = _HANDLE_RE.search(text)
                handle = h.group(1) if h else None
        elif name == "date" and year is None and el.get("dateType", "Issued") == "Issued":
            m = re.search(r"(19|20)\d\d", text)
            if m:
                year = int(m.group(0))
        elif name == "description":
            descriptions.append(text)
        elif name == "language" and lang is None:
            lang = text
    return {"iris_id": ident, "title": title, "year": year, "doi": doi, "handle": handle, "language": lang,
            "abstract": descriptions[0] if descriptions else None,
            "abstract_alt": descriptions[1] if len(descriptions) > 1 else None}


COLUMNS = ["iris_id", "title", "year", "doi", "handle", "language", "abstract", "abstract_alt"]


def parse(out: Path) -> pd.DataFrame:
    rows = []
    for page in sorted(out.glob("page_*.xml")):
        root = ET.fromstring(page.read_bytes())
        for rec in root.iter(f"{OAI}record"):
            r = _parse_record(rec)
            if r and r["title"]:
                rows.append(r)
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.astype({"iris_id": "string", "title": "string", "year": "Int64", "doi": "string", "handle": "string",
                      "language": "string", "abstract": "string", "abstract_alt": "string"})


def _harvest_dir() -> Path:
    """Resume an interrupted harvest if one exists, otherwise start a new dated snapshot."""
    base = config.RAW / "iris"
    for p in sorted(base.glob("*"), reverse=True) if base.exists() else []:
        prog = p / "progress.json"
        if p.is_dir() and prog.exists() and not json.loads(prog.read_text()).get("complete"):
            return p
    return base / dt.date.today().isoformat()


def run(cfg: dict, args=None) -> None:
    config.ensure_dirs()
    out = _harvest_dir()
    out.mkdir(parents=True, exist_ok=True)
    harvest(cfg, out)
    df = parse(out)
    df.to_parquet(config.INTERIM / "iris_records.parquet", index=False)
    log.info("IRIS records: %d, with DOI: %d, with handle: %d, with abstract: %d", len(df), df.doi.notna().sum(), df.handle.notna().sum(), df.abstract.notna().sum())
