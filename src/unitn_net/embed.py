"""Step `embed`: embeddings of publications (title + whole abstract) and courses (name + description).

A publication is embedded only if it has an abstract of at least `layers.min_abstract_words` words: the text is
"<title>. <abstract>", never the title alone. Likewise a course is embedded only if it has a description of at least
`layers.min_course_words` words ("<name>. <description>"). Texts longer than `max_tokens` are truncated and counted (`truncated`).
Both sides of every comparison are documents (document-document similarity), so the same `document_prefix` (empty for
Qwen3-Embedding, whose model card puts an instruction only on queries) is applied to every text; pooling and
normalisation come from the model's sentence-transformers configuration, nothing is re-implemented.

Cache key: (entity_type, entity_id, text_hash, model, revision). Unchanged rows are never recomputed, except rows that
were truncated under a different `max_tokens`.
Outputs: processed/embeddings[_<tag>].npy (float32, L2-normalised), processed/embeddings_index[_<tag>].parquet,
processed/embed_stats[_<tag>].json (truncation rate, runtime, VRAM peak, cache hit rate).
"""

from __future__ import annotations

import json
import logging
import time

import numpy as np
import pandas as pd

from . import config
from .textnorm import text_hash

log = logging.getLogger(__name__)
INDEX_COLS = ["row", "entity_type", "entity_id", "text_hash", "text_kind", "model", "revision", "truncated", "max_tokens"]


def has_abstract(abstract, min_words: int = 0) -> bool:
    return isinstance(abstract, str) and len(abstract.split()) >= max(min_words, 1)


def texts_for(pubs: pd.DataFrame, courses: pd.DataFrame, prefix: str = "", min_abstract_words: int = 0,
              min_course_words: int = 0) -> pd.DataFrame:
    rows = []
    for pid, title, abstract in zip(pubs.pub_id, pubs.title, pubs.abstract):
        if has_abstract(abstract, min_abstract_words):   # no abstract -> no vector: titles alone are not compared
            rows.append(("publication", pid, f"{prefix}{title}. {abstract}", "title_abstract"))
    for cid, name, desc in zip(courses.course_id, courses.name, courses.description):
        if has_abstract(desc, min_course_words):         # same rule as publications: a course name alone is not compared
            rows.append(("course", cid, f"{prefix}{name}. {desc}", "course"))
    df = pd.DataFrame(rows, columns=["entity_type", "entity_id", "text", "text_kind"])
    df["text_hash"] = df.text.map(text_hash)
    return df


def paths(tag: str) -> tuple:
    suffix = f"_{tag}" if tag else ""
    return (config.PROCESSED / f"embeddings{suffix}.npy", config.PROCESSED / f"embeddings_index{suffix}.parquet",
            config.PROCESSED / f"embed_stats{suffix}.json")


def _resolve_revision(model_name: str, revision: str) -> str:
    if revision:
        return revision
    from huggingface_hub import HfApi  # transitive dependency of sentence-transformers
    sha = HfApi().model_info(model_name).sha
    log.warning("embedding.revision is empty: resolved %s -> %s. Pin it in config.toml.", model_name, sha)
    return sha


def run(cfg: dict, args=None) -> None:
    import torch
    from sentence_transformers import SentenceTransformer

    config.ensure_dirs()
    ecfg = cfg["embedding_alt"] if getattr(args, "alt", False) else cfg["embedding"]
    tag = ecfg.get("tag", "")
    npy_path, idx_path, stats_path = paths(tag)
    pubs = pd.read_parquet(config.PROCESSED / "publications.parquet")
    courses = pd.read_parquet(config.INTERIM / "courses.parquet")
    texts = texts_for(pubs, courses, ecfg["document_prefix"], cfg["layers"].get("min_abstract_words", 0),
                      cfg["layers"].get("min_course_words", 0))
    revision = _resolve_revision(ecfg["model"], ecfg["revision"])

    old_idx = pd.read_parquet(idx_path) if idx_path.exists() else pd.DataFrame(columns=INDEX_COLS)
    old_emb = np.load(npy_path) if npy_path.exists() else np.zeros((0, 0), dtype=np.float32)
    key = ["entity_type", "entity_id", "text_hash"]
    if "max_tokens" not in old_idx.columns:
        old_idx = old_idx.assign(max_tokens=-1)
    cached = old_idx[(old_idx.model == ecfg["model"]) & (old_idx.revision == revision)
                     & (~old_idx.truncated.astype(bool) | (old_idx.max_tokens == ecfg["max_tokens"]))]   # truncated under another limit: redo
    merged = texts.merge(cached[key + ["row", "truncated"]], on=key, how="left")
    hit = merged.row.notna()
    log.info("cache: %d / %d texts reused (%.1f%%)", hit.sum(), len(merged), 100 * hit.mean() if len(merged) else 100.0)

    todo = merged[~hit]
    t0 = time.time()
    new_vecs = np.zeros((0, old_emb.shape[1] if old_emb.size else 0), dtype=np.float32)
    truncated = np.zeros(len(todo), dtype=bool)
    if len(todo):
        none = lambda d: {k: (None if v == "none" else v) for k, v in dict(d).items()}   # noqa: E731  (TOML has no null)
        model = SentenceTransformer(ecfg["model"], revision=revision, tokenizer_kwargs=dict(ecfg.get("tokenizer_kwargs", {})),
                                    config_kwargs=none(ecfg.get("config_kwargs", {})) or None,
                                    model_kwargs={"torch_dtype": getattr(torch, ecfg.get("dtype", "float32"))})
        model.max_seq_length = ecfg["max_tokens"]
        tok = model.tokenizer
        lengths = np.array([len(ids) for b in range(0, len(todo), 512)
                            for ids in tok(todo.text.iloc[b:b + 512].tolist(), truncation=False, padding=False)["input_ids"]])
        truncated = lengths > ecfg["max_tokens"]
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        new_vecs = model.encode(todo.text.tolist(), batch_size=ecfg["batch_size"], normalize_embeddings=True,
                                convert_to_numpy=True, show_progress_bar=True).astype(np.float32)
        if not np.isfinite(new_vecs).all():
            raise RuntimeError("the model returned NaN/inf embeddings (wrong dtype?): nothing was written")
    runtime = time.time() - t0

    all_vecs = np.concatenate([old_emb[merged.row[hit].astype(int).to_numpy()] if hit.any() else np.zeros((0, new_vecs.shape[1]), np.float32),
                               new_vecs])
    index = pd.concat([merged[hit].assign(truncated=merged.truncated[hit].astype(bool)),
                       todo.assign(truncated=truncated)], ignore_index=True)
    index = index[["entity_type", "entity_id", "text_hash", "text_kind", "truncated"]]
    index["row"] = np.arange(len(index))
    index["model"], index["revision"], index["max_tokens"] = ecfg["model"], revision, ecfg["max_tokens"]
    index = index[INDEX_COLS].astype({"row": "int64", "entity_type": "string", "entity_id": "string", "text_hash": "string",
                                      "text_kind": "string", "model": "string", "revision": "string", "truncated": "bool", "max_tokens": "int64"})
    np.save(npy_path, all_vecs)
    index.to_parquet(idx_path, index=False)
    stats = {"model": ecfg["model"], "revision": revision, "max_tokens": ecfg["max_tokens"], "n_texts": len(index), "n_encoded": int(len(todo)),
             "cache_hit_rate": float(hit.mean()) if len(merged) else 1.0, "runtime_s": round(runtime, 1),
             "truncation_rate_new": float(truncated.mean()) if len(todo) else 0.0,
             "truncation_rate_all": float(index.truncated.mean()) if len(index) else 0.0,
             "vram_peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if torch.cuda.is_available() and len(todo) else None,
             "dim": int(all_vecs.shape[1]) if all_vecs.size else 0,
             "text_kinds": index.text_kind.value_counts().to_dict()}
    stats_path.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    log.info("embeddings: %s", stats)
