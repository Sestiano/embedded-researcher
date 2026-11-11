"""Configuration (config.toml) and project paths."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"


def load(path: Path = ROOT / "config.toml") -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def latest_raw(source: str) -> Path:
    """Most recent dated download folder for a source, e.g. data/raw/opendata/2026-09-20."""
    base = RAW / source
    dirs = sorted(p for p in base.iterdir() if p.is_dir() and p.name[:1].isdigit()) if base.exists() else []  # skip e.g. robots/
    if not dirs:
        raise FileNotFoundError(f"no raw downloads under {base}; run the corresponding fetch step first")
    return dirs[-1]


def ensure_dirs() -> None:
    for d in (RAW, INTERIM, PROCESSED, REPORTS):
        d.mkdir(parents=True, exist_ok=True)
