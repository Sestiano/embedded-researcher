from unitn_net.fetch_openalex import reconstruct_abstract


def test_abstract_reconstruction():
    inv = {"network": [2], "faculty": [1], "The": [0], "of": [3, 5], "Trento": [4, 6]}
    assert reconstruct_abstract(inv) == "The faculty network of Trento of Trento"


def test_abstract_reconstruction_empty():
    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


def test_iris_abstracts_are_matched_in_the_publications_own_language():
    import pandas as pd
    from unitn_net.link import iris_abstracts_for_publications
    pubs = pd.DataFrame({"pub_id": ["p1", "p2", "p3"], "year": [2020, 2021, 2022], "doi": ["10.1234/a", None, None],
                         "title": ["Il ruolo della giustizia", "Compressive sensing for radar", "Solo titolo"],
                         "language": ["italiano", "inglese", "italiano"]})
    iris = pd.DataFrame({"iris_id": ["i1", "i2"], "year": [2020, 2021], "doi": ["10.1234/a", None],
                         "title": ["Il ruolo della giustizia", "Compressive sensing for radar"],
                         # i1: English abstract first, Italian second -> the Italian one must win for an Italian title
                         "abstract": ["This paper discusses the role of the justice and of the victims", "We study compressive sensing"],
                         "abstract_alt": ["Il contributo discute il ruolo della giustizia nella tutela delle vittime", None]})
    out = iris_abstracts_for_publications(pubs, iris).set_index("pub_id")
    assert out.abstract["p1"].startswith("Il contributo") and out.abstract["p2"].startswith("We study")
    assert "p3" not in out.index
    # an Italian publication whose only IRIS abstract is English gets none (never embedded across languages)
    only_en = iris.assign(abstract_alt=None)
    assert "p1" not in iris_abstracts_for_publications(pubs, only_en).pub_id.tolist()
