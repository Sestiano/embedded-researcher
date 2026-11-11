"""python -m unitn_net <step> — run one pipeline step (each step is idempotent and reads the previous outputs).

`all` runs normalize -> link -> embed -> layers -> graph -> evaluate -> export on the data already downloaded.
`build` downloads missing raw data (opendata, IRIS, and OpenAlex if OPENALEX_API_KEY is set) and runs the full pipeline.
"""

from __future__ import annotations

import argparse
import copy
import importlib
import logging
import os
from pathlib import Path

from . import config

STEPS = {  # in execution order; see README.md for the STOP points
    "fetch-opendata": "fetch_opendata",
    "audit": "audit",
    "normalize": "normalize",
    "fetch-iris": "fetch_iris",
    "fetch-openalex": "fetch_openalex",
    "link": "link",
    "embed": "embed",
    "layers": "layers",
    "graph": "graph",
    "evaluate": "evaluate",
    "export": "export",
    "serve": "serve",
}

ALL = ["normalize", "link", "embed", "layers", "graph", "evaluate", "export"]   # no downloads: the fetch steps are run by hand
ALT_STEPS = ["embed", "layers", "graph", "evaluate", "export"]


def build_plan(cfg: dict, include_alt: bool = False) -> list[tuple[str, bool]]:
    """Return the sequence of (step_name, is_alt) needed to build graph.json (and optionally graph_alt.json) from scratch."""
    plan: list[tuple[str, bool]] = []
    od_dir = config.RAW / "opendata"
    has_od = od_dir.exists() and any(p.is_dir() for p in od_dir.iterdir())
    if not has_od:
        plan.extend([("fetch-opendata", False), ("audit", False)])
    plan.append(("normalize", False))
    if not (config.INTERIM / "iris_records.parquet").exists():
        plan.append(("fetch-iris", False))
    oa_key_env = cfg.get("openalex", {}).get("api_key_env", "OPENALEX_API_KEY")
    if os.environ.get(oa_key_env) and not (config.INTERIM / "openalex_works.parquet").exists():
        plan.append(("fetch-openalex", False))
    for s in ("link", "embed", "layers", "graph", "evaluate", "export"):
        plan.append((s, False))
    if include_alt:
        for s in ALT_STEPS:
            plan.append((s, True))
    return plan


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m unitn_net", description=__doc__)
    ap.add_argument("step", choices=[*STEPS, "all", "build"])
    ap.add_argument("--alt", action="store_true", help="use the [embedding_alt] model (or include it in `build`)")
    ap.add_argument("--host", default="127.0.0.1", help="serve: address to listen on (0.0.0.0 = reachable from the network)")
    ap.add_argument("--port", type=int, default=8000, help="serve: port")
    ap.add_argument("--config", type=Path, default=config.ROOT / "config.toml")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    cfg = config.load(args.config)
    if args.step == "build":
        for step, is_alt in build_plan(cfg, include_alt=args.alt):
            step_args = copy.copy(args)
            step_args.alt = is_alt
            logging.getLogger("unitn_net").info("=== %s%s", step, " (--alt)" if is_alt else "")
            module = importlib.import_module(f"unitn_net.{STEPS[step]}")
            module.run(cfg, step_args)
    else:
        for step in (ALL if args.step == "all" else [args.step]):
            logging.getLogger("unitn_net").info("=== %s", step)
            module = importlib.import_module(f"unitn_net.{STEPS[step]}")  # lazy: `embed` imports torch
            module.run(cfg, args)


if __name__ == "__main__":
    main()
