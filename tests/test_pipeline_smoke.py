"""End-to-end smoke test on synthetic data that follows the documented open-data schemas.

No network, no model: `embed` is replaced by random unit vectors written in the same cache format.
Runs audit -> normalize -> link (with a fake OpenAlex table) -> layers -> graph -> export -> evaluate in a tmp dir.
"""

import json
import random

import numpy as np
import pandas as pd
import pytest

from unitn_net import audit, config, embed, evaluate, export, layers, link, normalize, opendata

pytest.importorskip("igraph")
from unitn_net import graph  # noqa: E402

CFG = config.load()
N_PEOPLE, N_PUBS, N_COURSES = 30, 240, 40
WORDS = "network language perception model learning neural cortex syntax semantics inference bayesian corpus speech vision".split()


def _title(rng):
    return " ".join(rng.choice(WORDS) for _ in range(6)).capitalize()


def make_raw(root, rng):
    date = root / "opendata" / "2026-01-01"
    people = []
    for i in range(N_PEOPLE):
        role = ["professore ordinario", "professore associato", "ricercatore", "assegnista"][i % 4]
        people.append({"id": f"PER{i:07d}", "nome": f"Nome{i}", "cognome": f"Cognome{i}", "telefono": "0461 000000",
                       "posizioni": [{"descrizioneRuolo": role.title(), "nomeStruttura": f"Dipartimento {i % 3}", "idStruttura": f"D{i % 3}"}],
                       "SSD": f"SSD-{i % 5}", "CUN": f"{i % 2}"})
    staff_ids = [p["id"] for p in people]
    pubs_by_year = {}
    works = []
    for k in range(N_PUBS):
        year = 2012 + k % 14
        authors = rng.sample(staff_ids, rng.choice([1, 1, 2, 3]))
        title = _title(rng)
        doi = f"10.1000/test.{k}" if k % 3 else None
        rec = {"tipo": "articolo", "titolo": title, "abstract": " ".join(rng.choice(WORDS) for _ in range(30)) if k % 4 else "",
               "anno": 9999 if k % 40 == 0 else year, "lingua": "en" if k % 5 else "it",
               "autori": [{"nome": "x", "cognome": "y", "id": a} for a in authors],
               "citazione": f"Ref {k}. https://doi.org/{doi}" if doi else f"Ref {k}"}
        pubs_by_year.setdefault(year, []).append(rec)
        if doi:
            works.append({"openalex_id": f"W{k}", "doi": doi, "title": title, "year": year, "language": "en",
                          "abstract": None, "cited_by_count": 0, "author_names": [f"Nome Cognome{int(a[3:])}" for a in authors],
                          "primary_topic": None, "n_references": 0})
    pubs_by_year[2015].append(dict(pubs_by_year[2015][0]))  # duplicate across files
    courses = []
    for c in range(N_COURSES):
        courses.append({"nome": f"Corso {c}", "descrizione": " ".join(rng.choice(WORDS) for _ in range(12)),
                        "corsoStudi": f"CdS {c % 6}", "dipartimento": {"nome": f"Dipartimento {c % 3}", "id": f"D{c % 3}"},
                        "docenti": [{"nome": "x", "cognome": "y", "id": rng.choice(staff_ids)}], "assistenti": []})
    units = [{"id": f"D{i}", "nome": f"Dipartimento {i}", "idPadre": "ATENEO"} for i in range(3)]

    def write(slug, resources):
        d = date / slug
        d.mkdir(parents=True)
        pkg = {"resources": [{"id": f"r{n}", "name": name, "format": "JSON", "description": ""} for n, (name, _) in enumerate(resources)]}
        (d / "package.json").write_text(json.dumps(pkg))
        for n, (_, recs) in enumerate(resources):
            (d / f"r{n}.json").write_text(json.dumps(recs, ensure_ascii=False))

    write(opendata.STAFF, [("personale", people)])
    write(opendata.PUBS, [(f"pubblicazioni {y}", recs) for y, recs in sorted(pubs_by_year.items())])
    write(opendata.COURSES, [("insegnamenti 2025/2026", courses[:30]), ("insegnamenti 2024-25", courses[30:])])
    write(opendata.UNITS, [("unita", units)])
    refs = [(w["openalex_id"], f"R{rng.randrange(60)}") for w in works for _ in range(3)]
    refs += [(works[i]["openalex_id"], works[j]["openalex_id"]) for i in range(0, len(works), 7) for j in (i + 1, i + 2) if j < len(works)]
    return pd.DataFrame(works), pd.DataFrame(refs, columns=["openalex_id", "referenced_openalex_id"])


def fake_embeddings(rng):
    pubs = pd.read_parquet(config.PROCESSED / "publications.parquet")
    courses = pd.read_parquet(config.INTERIM / "courses.parquet")
    texts = embed.texts_for(pubs, courses, min_abstract_words=CFG["layers"]["min_abstract_words"], min_course_words=5)
    assert (texts.entity_type == "publication").sum() == pubs.abstract.notna().sum() < len(pubs)   # no abstract, no vector
    vecs = rng.normal(size=(len(texts), 16)).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    np.save(config.PROCESSED / "embeddings.npy", vecs)
    idx = texts.assign(row=np.arange(len(texts)), model="fake", revision="0", truncated=False, max_tokens=0)[embed.INDEX_COLS]
    idx.to_parquet(config.PROCESSED / "embeddings_index.parquet", index=False)


def test_pipeline_smoke(tmp_path, monkeypatch):
    rng = random.Random(0)
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "RAW", tmp_path / "raw")
    monkeypatch.setattr(config, "INTERIM", tmp_path / "interim")
    monkeypatch.setattr(config, "PROCESSED", tmp_path / "processed")
    monkeypatch.setattr(config, "REPORTS", tmp_path / "reports")
    monkeypatch.delenv(CFG["openalex"]["api_key_env"], raising=False)
    config.ensure_dirs()
    (tmp_path / "optout.csv").write_text("person_id\nPER0000000\n", encoding="utf-8")
    works, refs = make_raw(config.RAW, rng)
    cfg = json.loads(json.dumps(CFG))
    cfg["layers"]["min_papers_sem"] = 2
    cfg["scope"]["roles"] = ["professore ordinario", "professore associato", "ricercat"]  # independent of the real scope
    cfg["evaluation"]["bootstrap_reps"] = 20

    audit.run(cfg)
    assert "descrizioneRuolo" in (config.REPORTS / "00_data_audit.md").read_text()

    normalize.run(cfg)
    people = pd.read_parquet(config.INTERIM / "people.parquet")
    assert "PER0000000" not in set(people.person_id)
    assert len(people) == sum(1 for i in range(N_PEOPLE) if i % 4 != 3) - 1 and "telefono" not in people.columns
    pubs = pd.read_parquet(config.INTERIM / "publications.parquet")
    stats = json.loads((config.INTERIM / "normalize_stats.json").read_text())
    assert stats["duplicates"] == 1 and pubs.in_press.sum() == N_PUBS // 40
    assert set(pubs.doi_source.dropna()) == {"citation_regex"}

    works.to_parquet(config.INTERIM / "openalex_works.parquet", index=False)
    refs.to_parquet(config.INTERIM / "oa_references.parquet", index=False)
    link.run(cfg)
    ppubs = pd.read_parquet(config.PROCESSED / "publications.parquet")
    assert (ppubs.link_method == "doi").sum() == ppubs.doi.notna().sum()
    assert (config.REPORTS / "01_linking.md").exists()

    fake_embeddings(np.random.default_rng(0))
    layers.run(cfg)
    edges = pd.read_parquet(config.PROCESSED / "edges.parquet")
    assert len(edges) > 0 and (edges.person_i < edges.person_j).all()
    assert edges.evidence.map(json.loads).map(bool).all()
    avail = pd.read_parquet(config.PROCESSED / "person_layers.parquet")
    assert avail.has_coauth.all()

    graph.run(cfg)
    export.run(cfg)
    gj = json.loads((config.PROCESSED / "graph.json").read_text(encoding="utf-8"))
    assert len(gj["nodes"]) == len(people) and len(gj["edges"]) == len(edges)
    assert all(n["id"] != "PER0000000" for n in gj["nodes"])
    assert "2.0" in gj["meta"]["partitions"] and "1.0" in gj["meta"]["partitions"]
    assert "telefono" not in json.dumps(gj) and "0461" not in json.dumps(gj)
    assert all(set(e["p"]) <= set(layers.LAYERS) for e in gj["edges"])

    evaluate.run(cfg)
    report = (config.REPORTS / "04_evaluation.md").read_text()
    assert "## 2. Temporal link prediction" in report and "baseline_random" in report
    assert (config.REPORTS / "audit.csv").exists()
