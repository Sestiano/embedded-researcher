"""Step `export`: processed tables -> data/processed/graph.json for the static web UI.

Only the fields the UI needs are exported (explicit allow-list): no phone numbers, no emails.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

import numpy as np
import pandas as pd

from . import config
from .layers import LAYERS

log = logging.getLogger(__name__)


def attribution() -> str:
    """Credit only the sources that are actually in the build (OpenAlex was credited before it was ever queried)."""
    parts = ["Università di Trento open data (CC BY 4.0)"]
    if (config.INTERIM / "iris_records.parquet").exists():
        parts.append("IRIS UniTrento (abstracts)")
    if (config.INTERIM / "openalex_works.parquet").exists():
        parts.append("OpenAlex (CC0)")
    return "Data: " + ", ".join(parts)


def run(cfg: dict, args=None) -> None:
    alt = bool(getattr(args, "alt", False))
    tag = cfg.get("embedding_alt", {}).get("tag", "alt") if alt else ""
    suf = f"_{tag}" if tag else ""
    people = pd.read_parquet(config.INTERIM / "people.parquet")
    edges = pd.read_parquet(config.PROCESSED / f"edges{suf}.parquet")
    comm = pd.read_parquet(config.PROCESSED / f"communities{suf}.parquet")
    layout = pd.read_parquet(config.PROCESSED / f"layout{suf}.parquet")
    avail = pd.read_parquet(config.PROCESSED / f"person_layers{suf}.parquet")
    courses = pd.read_parquet(config.INTERIM / "courses.parquet")
    teaching = pd.read_parquet(config.INTERIM / "teaching.parquet")
    meta = json.loads((config.PROCESSED / f"graph_meta{suf}.json").read_text(encoding="utf-8"))

    latest_year = courses.academic_year[courses.academic_year != "unknown"].max() if len(courses) else None
    current = teaching.merge(courses[courses.academic_year == latest_year] if latest_year else courses.iloc[0:0], on="course_id")
    courses_of = current.groupby("person_id").apply(
        lambda d: [{"name": r.name, "programme": _s(r.degree_programme), "year": r.academic_year, "role": r.teaching_role}
                   for r in d.itertuples()], include_groups=False).to_dict()

    nodes_df = people.merge(comm, on="person_id").merge(layout, on="person_id").merge(avail, on="person_id")
    nodes = [{
        "id": r.person_id, "label": f"{r.given_name} {r.family_name}", "role": _s(r.role), "dept": _s(r.dept_name),
        "dept_id": _s(r.dept_id), "affiliations": [a for a in (_s(r.affiliations) or "").split("|") if a], "ssd": _s(r.ssd), "cun": _s(r.cun), "community": int(r.community_id),
        "n_pubs": int(r.n_pubs), "x": float(r.x), "y": float(r.y),
        "layers": {l: bool(getattr(r, f"has_{l}")) for l in LAYERS}, "sem_conf": _f(r.sem_confidence),
        "courses": courses_of.get(r.person_id, []),
    } for r in nodes_df.itertuples()]

    out_edges = []
    for r in edges.itertuples():
        p = {l: _f(getattr(r, f"{l}_p")) for l in LAYERS}
        raw = {l: _f(getattr(r, l)) for l in LAYERS}
        out_edges.append({"s": r.person_i, "t": r.person_j, "p": {k: v for k, v in p.items() if v is not None},
                          "raw": {k: v for k, v in raw.items() if v is not None}, "ev": json.loads(r.evidence),
                          "conf": {"sem": _f(r.sem_conf)} if _f(r.sem_conf) is not None else {},
                          "unexplored": bool(r.unexplored), "co_teach": bool(getattr(r, "co_teach", False))})

    alt_file = config.PROCESSED / "graph_alt.json"
    if not alt and alt_file.exists() and alt_file.stat().st_mtime < (config.INTERIM / "people.parquet").stat().st_mtime:
        # built before the last `normalize`: it may still list people who have since opted out. Never serve it.
        alt_file.unlink()
        log.warning("removed stale %s (older than people.parquet): rerun `layers --alt`, `graph --alt`, `export --alt`", alt_file.name)
    alt_avail = alt or alt_file.exists()
    graph = {
        "meta": {"snapshot_date": config.latest_raw("opendata").name, "build_date": dt.date.today().isoformat(),
                 "attribution": attribution(), "layers": LAYERS, "weights": cfg["weights"],
                 "unexplored_percentile": cfg["layers"]["unexplored_percentile"], "confidence": cfg.get("confidence", {}), "top_k": cfg["layers"]["top_k"],
                 "modularity": float(np.mean(meta["modularity_by_seed"])), "ari": meta["mean_pairwise_ari"],
                 "resolution": meta.get("resolution", cfg.get("graph", {}).get("resolution", 2.0)),
                 "partitions": meta.get("partitions", {}),
                 "contact_email": cfg.get("contact", {}).get("email", ""),
                 "model": cfg.get("embedding_alt" if alt else "embedding", {}).get("model", ""),
                 "models": {"default": cfg.get("embedding", {}).get("model", "Qwen/Qwen3-Embedding-0.6B"),
                            "alt": cfg.get("embedding_alt", {}).get("model", "google/embeddinggemma-2")},
                 "alt_available": alt_avail},
        "communities": [{"id": int(c), "label": meta["labels"].get(str(c), ""), "name": meta.get("names", {}).get(str(c), ""), "size": meta["sizes"][str(c)]} for c in sorted(map(int, meta["sizes"]))],
        "nodes": nodes, "edges": out_edges,
    }
    out = config.PROCESSED / f"graph{suf}.json"
    out.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("wrote %s: %d nodes, %d edges, %.1f MB", out, len(nodes), len(out_edges), out.stat().st_size / 1e6)


def _s(v) -> str | None:
    return None if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA else str(v)


def _f(v) -> float | None:
    return None if v is None or pd.isna(v) else round(float(v), 4)
