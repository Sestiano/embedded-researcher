import numpy as np
import pandas as pd
import pytest

from unitn_net import layers
from unitn_net.layers import Inputs, composite, percentiles, set_similarity

CFG = {"layers": {"top_k": 10, "min_papers_sem": 2, "recency_tau": 0, "sem_candidates": 10,
                  "edge_layers": ["sem", "coupling", "direct", "coauth", "teach"], "unexplored_percentile": 0.9},
       "weights": {"sem": 0.35, "coupling": 0.20, "direct": 0.10, "coauth": 0.10, "teach": 0.15, "field": 0.10}}


def test_set_similarity_hand_computed_3x2():
    S = np.array([[0.9, 0.1],
                  [0.2, 0.8],
                  [0.5, 0.4]])
    # mean_a max_b = (0.9 + 0.8 + 0.5) / 3 ; mean_b max_a = (0.9 + 0.8) / 2
    expected = 0.5 * ((0.9 + 0.8 + 0.5) / 3 + (0.9 + 0.8) / 2)
    assert set_similarity(S, np.ones(3), np.ones(2)) == pytest.approx(expected)
    # weights: a-side weighted mean with weights (1, 1, 2) -> (0.9 + 0.8 + 2 * 0.5) / 4
    expected_w = 0.5 * ((0.9 + 0.8 + 1.0) / 4 + (0.9 + 0.8) / 2)
    assert set_similarity(S, np.array([1, 1, 2]), np.ones(2)) == pytest.approx(expected_w)


def test_composite_skips_nan_layers():
    P = {"sem": np.array([0.8, np.nan, np.nan]), "coauth": np.array([0.2, 0.6, np.nan]), "field": np.array([1.0, np.nan, np.nan])}
    w = {"sem": 0.5, "coauth": 0.3, "field": 0.2}
    c = composite(P, w)
    assert c[0] == pytest.approx((0.5 * 0.8 + 0.3 * 0.2 + 0.2 * 1.0) / 1.0)
    assert c[1] == pytest.approx(0.6)        # only coauth defined: no zero-filling of the others
    assert np.isnan(c[2])                    # nothing defined -> NaN


def test_percentiles_average_ties_and_keep_nan():
    M = np.array([[np.nan, 0.5, 0.5, np.nan],
                  [0.5, np.nan, 0.9, 0.1],
                  [0.5, 0.9, np.nan, np.nan],
                  [np.nan, 0.1, np.nan, np.nan]])
    P = percentiles(M)
    # non-NaN pairs: (0,1)=0.5, (0,2)=0.5, (1,2)=0.9, (1,3)=0.1 -> ranks 2.5, 2.5, 4, 1 over 4
    assert P[0, 1] == pytest.approx(2.5 / 4) and P[0, 2] == pytest.approx(2.5 / 4)
    assert P[1, 2] == pytest.approx(1.0) and P[1, 3] == pytest.approx(0.25)
    assert P[2, 1] == P[1, 2] and np.isnan(P[0, 3])


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def _inputs():
    """3 people. P1: A, B, C ; P2: C, D, E, F ; P3: G, H, I. C is co-authored by P1 and P2."""
    people = pd.DataFrame({"person_id": ["P1", "P2", "P3"], "dept_id": ["D1", "D2", "D1"],
                           "ssd": ["X", "X", "Y"], "cun": ["1", None, "1"]}).astype("string")
    pub_ids = list("ABCDEFGHI")
    pubs = pd.DataFrame({"pub_id": pub_ids, "title": [f"title {p}" for p in pub_ids], "year": [2020] * 9,
                         "in_press": [False] * 9, "doi": [None] * 9,
                         "openalex_id": ["WA", "WB", "WC", "WD", None, None, "WG", None, None]})
    pubs["year"] = pubs.year.astype("Int64")
    authorship = pd.DataFrame([("A", "P1"), ("B", "P1"), ("C", "P1"), ("C", "P2"), ("D", "P2"), ("E", "P2"), ("F", "P2"),
                               ("G", "P3"), ("H", "P3"), ("I", "P3")], columns=["pub_id", "person_id"])
    vecs = {"A": [1, 0, 0, 0], "B": [1, 1, 0, 0], "C": [0, 0, 1, 0], "D": [0, 1, 0, 0], "E": [0, 1, 1, 0],
            "F": [0, 0, 1, 1], "G": [0, 0, 0, 1], "H": [1, 0, 0, 1], "I": [0, 1, 0, 1],
            "c1": [1, 0, 0, 0], "c2": [0, 1, 0, 0]}
    emb = np.stack([_unit(vecs[k]) for k in vecs])
    emb_index = pd.DataFrame({"row": range(len(vecs)), "entity_id": list(vecs),
                              "entity_type": ["publication"] * 9 + ["course"] * 2,
                              "text_kind": ["title_abstract"] * 9 + ["course"] * 2})
    courses = pd.DataFrame({"course_id": ["c1", "c2"], "name": ["Course 1", "Course 2"], "degree_programme": ["CS", "Math"],
                            "academic_year": ["2025/2026"] * 2})
    teaching = pd.DataFrame([("c1", "P1"), ("c1", "P2"), ("c2", "P2")], columns=["course_id", "person_id"])
    oa_refs = pd.DataFrame([("WA", "R1"), ("WA", "R2"), ("WB", "R2"), ("WC", "R1"), ("WC", "R3"), ("WD", "R3"), ("WD", "R2"),
                            ("WD", "WA"), ("WC", "WA")], columns=["openalex_id", "referenced_openalex_id"])
    return Inputs(people, pubs, authorship, emb, emb_index, courses, teaching, oa_refs, current_year=2026), emb, vecs


def test_coauthored_papers_are_excluded_from_sem():
    inp, emb, vecs = _inputs()
    res = layers.compute(CFG, inp)
    rows = {k: i for i, k in enumerate(vecs)}
    E1 = emb[[rows["A"], rows["B"]]]            # P1 without C
    E2 = emb[[rows["D"], rows["E"], rows["F"]]]  # P2 without C
    expected = set_similarity(E1 @ E2.T, np.ones(2), np.ones(3))
    assert res.raw["sem"][0, 1] == pytest.approx(expected, abs=1e-6)
    naive = set_similarity(emb[[rows["A"], rows["B"], rows["C"]]] @ emb[[rows["C"], rows["D"], rows["E"], rows["F"]]].T, np.ones(3), np.ones(4))
    assert naive > expected  # the shared paper would have inflated the score
    assert res.raw["sem"][0, 1] == res.raw["sem"][1, 0]
    assert np.isnan(res.raw["sem"][0, 0])


def test_coauthored_works_are_excluded_from_coupling_and_direct():
    inp, _, _ = _inputs()
    res = layers.compute(CFG, inp)
    # references: WA -> R1 R2 WA?  (self excluded: WA has no 'WA' ref); WB -> R2; WC -> R1 R3 WA; WD -> R3 R2 WA. 5 works: WA WB WC WD WG.
    # ref columns: R1, R2, R3, WA. df: R1=2, R2=3, R3=2, WA=2 -> idf = log(5/df)
    idf = {"R1": np.log(5 / 2), "R2": np.log(5 / 3), "R3": np.log(5 / 2), "WA": np.log(5 / 2)}
    v1 = np.array([idf["R1"], 2 * idf["R2"], 0, 0])              # P1 own works: WA, WB (WC excluded)
    v2 = np.array([0, idf["R2"], idf["R3"], idf["WA"]])          # P2 own works: WD
    expected = v1 @ v2 / (np.linalg.norm(v1) * np.linalg.norm(v2))
    assert res.raw["coupling"][0, 1] == pytest.approx(expected, abs=1e-6)
    assert np.isnan(res.raw["coupling"][0, 2])   # WG has no references
    # direct: only WD -> WA counts for (P1, P2) (WC -> WA is a co-authored work); (P1,P3) and (P2,P3) have 0 citations
    assert res.raw["direct"][0, 1] == pytest.approx(1.0)  # log1p(1) min-max normalised against two zero pairs
    assert res.raw["direct"][0, 2] == pytest.approx(0.0)
    assert res.evidence["direct"](0, 1) == [{"citing": "title D", "cited": "title A"}]


def test_coauth_teach_field_layers():
    inp, emb, vecs = _inputs()
    res = layers.compute(CFG, inp)
    assert res.raw["coauth"][0, 1] == pytest.approx(1.0)  # one shared paper, max over pairs
    assert res.raw["coauth"][0, 2] == 0.0
    rows = {k: i for i, k in enumerate(vecs)}
    c1 = emb[rows["c1"]]
    c2 = _unit(emb[[rows["c1"], rows["c2"]]].mean(0))
    # content 0.4 x cosine of the centroids, programmes 0.3 x Jaccard({CS}, {CS, Math}), co_teaching 0.3 x (1 - 0.5^1): c1 is shared
    expected_teach = 0.4 * float(c1 @ c2) + 0.3 * (1 / 2) + 0.3 * 0.5
    assert res.raw["teach"][0, 1] == pytest.approx(expected_teach, abs=1e-6)
    assert np.isnan(res.raw["teach"][0, 2])
    assert res.raw["field"][0, 1] == 1.0 and res.raw["field"][0, 2] == 0.5 and res.raw["field"][1, 2] == 0.0
    assert list(res.availability.has_teach) == [True, True, False]
    assert list(res.availability.n_pubs) == [3, 4, 3]


def test_select_edges_positive_defined_only():
    raw = {"x": np.array([[np.nan, 0.0, 0.7], [0.0, np.nan, np.nan], [0.7, np.nan, np.nan]])}
    assert layers.select_edges(raw, ["x"], 10) == {(0, 2)}


def _with_langs(langs: dict[str, str]):
    inp, emb, vecs = _inputs()
    inp.pubs["text_lang"] = inp.pubs.pub_id.map(langs)
    return inp


def test_sem_within_language_never_compares_across_languages():
    cfg = {**CFG, "layers": {**CFG["layers"], "sem_within_language": True}}
    base = dict.fromkeys("ABCDEFGHI", "it")
    # P1 (A, B: it) vs P2 (D, E, F: en) -> no shared language -> NaN, even though the cross-language cosines are defined
    langs = {**base, **dict.fromkeys("DEF", "en")}
    res = layers.compute(cfg, _with_langs(langs))
    assert np.isnan(res.raw["sem"][0, 1])
    off = layers.compute({**CFG, "layers": {**CFG["layers"], "sem_within_language": False}}, _with_langs(langs))
    assert np.isfinite(off.raw["sem"][0, 1])


def test_sem_within_language_uses_only_the_shared_language():
    cfg = {**CFG, "layers": {**CFG["layers"], "sem_within_language": True}}
    # D, E are it, F is en: only the it side (A, B vs D, E) is scored; F must not change the result
    a = layers.compute(cfg, _with_langs({**dict.fromkeys("ABCDEGHI", "it"), "F": "en"})).raw["sem"][0, 1]
    b = layers.compute(cfg, _with_langs({**dict.fromkeys("ABCDEGHI", "it"), "F": "other"})).raw["sem"][0, 1]
    assert np.isfinite(a) and a == pytest.approx(b)


def test_composite_confidence_scales_the_layer_weight_without_zero_filling():
    P = {"sem": np.array([1.0, 1.0]), "coauth": np.array([0.0, np.nan])}
    w = {"sem": 0.5, "coauth": 0.5}
    plain = composite(P, w)
    conf = composite(P, w, {"sem": np.array([0.5, 0.5])})
    assert plain[0] == pytest.approx(0.5)
    assert conf[0] == pytest.approx(0.25 / 0.75)            # sem counts half as much
    assert conf[1] == pytest.approx(1.0)                    # only sem defined: its confidence does not shrink the value


def test_publications_without_an_abstract_vector_take_no_part_in_sem():
    inp, emb, vecs = _inputs()
    full = layers.compute(CFG, inp).raw["sem"][0, 1]
    # drop the vector of F (P2 keeps D, E): the score is the one of A, B against D, E only
    inp.emb_index = inp.emb_index[inp.emb_index.entity_id != "F"]
    rows = {k: i for i, k in enumerate(vecs)}
    expected = set_similarity(emb[[rows["A"], rows["B"]]] @ emb[[rows["D"], rows["E"]]].T, np.ones(2), np.ones(2))
    res = layers.compute(CFG, inp)
    assert res.raw["sem"][0, 1] == pytest.approx(expected, abs=1e-6) and expected != pytest.approx(full)
    assert list(res.availability.n_pubs_embedded) == [3, 3, 3] and list(res.availability.n_pubs) == [3, 4, 3]
    # with a single abstract left P2 falls under min_papers_sem: undefined, not zero
    inp.emb_index = inp.emb_index[~inp.emb_index.entity_id.isin(["E", "C"])]
    assert np.isnan(layers.compute(CFG, inp).raw["sem"][0, 1])


def test_sem_confidence_grows_with_the_number_of_abstracts_and_follows_the_weaker_side():
    inp, _, _ = _inputs()
    res = layers.compute({**CFG, "confidence": {"half_evidence": 5.0}}, inp)
    # P1 has 3 abstracts, P2 has 4: the pair takes the weaker side, 3 / (3 + 5)
    assert res.sem_conf[0, 1] == pytest.approx(3 / 8)
    assert list(res.availability.sem_confidence) == pytest.approx([3 / 8, 4 / 9, 3 / 8])
    assert np.isnan(res.sem_conf[0, 2]) == np.isnan(res.raw["sem"][0, 2])  # defined exactly where sem is


def test_teach_evidence_lists_the_courses_taught_by_both():
    inp, _, _ = _inputs()
    assert layers.compute(CFG, inp).evidence["teach"](0, 1)["shared"] == ["Course 1"]


def test_teach_without_course_descriptions_uses_the_plain_components_only():
    inp, _, _ = _inputs()
    inp.emb_index = inp.emb_index[inp.emb_index.entity_type != "course"]     # no course has a description vector
    res = layers.compute(CFG, inp)
    assert res.raw["teach"][0, 1] == pytest.approx((0.3 * 0.5 + 0.3 * 0.5) / 0.6)   # content undefined: not counted as zero
    assert res.evidence["teach"](0, 1) == {"shared": ["Course 1"], "programmes": ["CS"], "courses": []}
