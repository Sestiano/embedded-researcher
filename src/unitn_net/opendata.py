"""Readers for the raw open-data downloads (shared by audit and normalize)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

STAFF = "personale-accademico-e-tecnico-amministrativo-dell-universita-di-trento"
PUBS = "pubblicazioni-universita-di-trento"
COURSES = "insegnamenti-universita-di-trento"
UNITS = "unita-organizzative-dell-universita-di-trento"


def records(obj: object, where: str = "") -> list[dict]:
    """The list of records in a resource JSON, whether top-level or wrapped in a single-key dict."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        lists = [v for v in obj.values() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0]
        dicts = [v for v in obj.values() if isinstance(v, dict)]
        if not lists and len(dicts) == 1:  # e.g. {"value": {"data": [...]}, "statusCode": 200}
            return records(dicts[0], where)
    raise ValueError(f"unrecognised resource structure in {where}: {type(obj).__name__} "
                     f"with keys {list(obj)[:10] if isinstance(obj, dict) else '-'}")


def package(raw_dir: Path, slug: str) -> dict:
    return json.loads((raw_dir / slug / "package.json").read_text(encoding="utf-8"))


def load_resources(raw_dir: Path, slug: str) -> list[tuple[dict, list[dict]]]:
    """(resource metadata, records) for every downloaded JSON resource of a dataset, in catalogue order."""
    out = []
    for res in package(raw_dir, slug)["resources"]:
        paths = list((raw_dir / slug).glob(f"{res['id']}.*"))
        if not paths:
            log.warning("%s: resource %s (%s) not downloaded", slug, res["id"], res.get("name"))
            continue
        path = paths[0]
        if path.suffix.lower() != ".json":
            log.info("%s: skipping non-JSON resource %s", slug, path.name)
            continue
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        out.append((res, records(obj, str(path))))
    return out
