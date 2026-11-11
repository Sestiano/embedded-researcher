from unitn_net.textnorm import extract_doi, norm_doi, norm_text, pub_id


def test_doi_normalization():
    assert norm_doi("https://doi.org/10.1000/ABC.123") == "10.1000/abc.123"
    assert norm_doi("doi:10.1000/xyz)") == "10.1000/xyz"
    assert norm_doi("http://dx.doi.org/10.1234/j.foo.2020.01.001.") == "10.1234/j.foo.2020.01.001"
    assert norm_doi("not a doi") is None
    assert norm_doi(None) is None
    assert norm_doi("") is None


def test_doi_extraction_from_citation():
    cit = "Rossi, M. (2021). A title. Journal, 3(2), 1-10. https://doi.org/10.5555/Test.2021,"
    assert extract_doi(cit) == "10.5555/test.2021"
    assert extract_doi("no identifier here") is None


def test_norm_text_strips_accents_and_punctuation():
    assert norm_text("Città  di TRENTO: un'analisi") == "citta di trento un analisi"
    assert norm_text(None) == ""


def test_pub_id_stability():
    a = pub_id("A Title", 2020, "Rossi (2020) A Title")
    assert a == pub_id("a title", 2020, "rossi 2020 a title")   # case/punctuation invariant
    assert a == pub_id("A  Títle", 2020, "Rossi (2020) A Title")  # accents/whitespace invariant
    assert a != pub_id("A Title", 2021, "Rossi (2020) A Title")   # year matters
    assert a != pub_id("A Title", None, "Rossi (2020) A Title")   # in press differs from dated
    assert len(a) == 40


def test_detect_lang_and_fallback():
    from unitn_net.textnorm import detect_lang, text_lang
    assert detect_lang("Il ruolo della giustizia riparativa nella tutela delle vittime") == "it"
    assert detect_lang("A study of the effects of temperature on the growth of bacteria") == "en"
    assert detect_lang("Compressive sensing") is None                      # no function words: undecided
    assert text_lang("Compressive sensing", None, "inglese") == "en"       # falls back to the declared language
    assert text_lang("Compressive sensing", None, "francese") == "other"
    assert text_lang("Il paesaggio della valle", "Abstract in italiano che descrive la ricerca", "inglese") == "it"  # detection wins


def test_primary_structure_prefers_a_department_and_all_structures_are_kept():
    from unitn_net.normalize import people_table
    rec = {"id": "x", "nome": "A", "cognome": "B", "ssd": "S", "cun": "", "posizioni": [
        {"ruolo": "Dottorando", "nomeStruttura": "Corso di Dottorato (D.M.226/2021) - Fisica", "idStruttura": "D"},
        {"ruolo": "Dottorando", "nomeStruttura": "Centro Interdipartimentale Mente/Cervello - CIMEC", "idStruttura": "C"},
        {"ruolo": "Dottorando", "nomeStruttura": "Dipartimento di Fisica", "idStruttura": "F"},
        {"ruolo": "Ospite", "nomeStruttura": "Rettorato", "idStruttura": "R"}]}
    row = people_table([rec], ["dottorand"]).iloc[0]
    assert row.dept_name == "Dipartimento di Fisica" and row.dept_id == "F"
    assert row.affiliations.split("|") == ["Corso di Dottorato (D.M.226/2021) - Fisica", "Centro Interdipartimentale Mente/Cervello - CIMEC", "Dipartimento di Fisica"]


def test_manual_affiliations_add_structures_and_never_guess_on_shared_names(tmp_path):
    import pandas as pd
    from unitn_net.normalize import apply_manual_affiliations
    people = pd.DataFrame({"given_name": ["Mario", "Anna", "Anna"], "family_name": ["Bianchi", "Rossi", "Rossi"],
                           "affiliations": ["Dipartimento di Psicologia e Scienze Cognitive", "Dipartimento di Fisica", "Dipartimento di Matematica"]})
    csv = tmp_path / "manual.csv"
    csv.write_text("given_name,family_name,structure\nMario,Bianchi,Centro Interdipartimentale Mente/Cervello - CIMEC\n"
                   "Mario,Bianchi,Scuola di Studi Internazionali - SSI\nMario,Bianchi,Centro Interdipartimentale Mente/Cervello - CIMEC\n"
                   "Anna,Rossi,Centro X\n", encoding="utf-8")
    out = apply_manual_affiliations(people, csv)
    assert out.affiliations[0].split("|") == ["Dipartimento di Psicologia e Scienze Cognitive", "Centro Interdipartimentale Mente/Cervello - CIMEC",
                                              "Scuola di Studi Internazionali - SSI"]   # several rows -> several structures, no duplicates
    assert out.affiliations[1] == "Dipartimento di Fisica" and out.affiliations[2] == "Dipartimento di Matematica"   # two Anna Rossi: skipped
    assert apply_manual_affiliations(people, tmp_path / "missing.csv").equals(people)


def test_optout_excludes_people_by_id_or_unambiguous_name(tmp_path):
    import pandas as pd
    from unitn_net.normalize import apply_optout
    people = pd.DataFrame({"person_id": ["P1", "P2", "P3", "P4"], "given_name": ["Mario", "Anna", "Anna", "Luca"],
                           "family_name": ["Bianchi", "Rossi", "Rossi", "Verdi"]})
    csv = tmp_path / "optout.csv"
    csv.write_text("person_id,given_name,family_name\nP1,,\n,Luca,Verdi\n,Anna,Rossi\n", encoding="utf-8")
    out = apply_optout(people, csv)
    # P1 excluded by id, P4 (Luca Verdi) excluded by unambiguous name, P2/P3 (two Anna Rossi) kept unless person_id is given
    assert list(out.person_id) == ["P2", "P3"]
    assert apply_optout(people, tmp_path / "missing.csv").equals(people)


def test_community_terms_skip_inflections_but_not_different_words():
    from unitn_net.graph import _same_stem
    for a, b in [("firm", "firms"), ("photon", "photons"), ("stimulus", "stimuli"), ("political", "politics"), ("politics", "politiche")]:
        assert _same_stem(a, b), (a, b)
    for a, b in [("quantum", "quantitative"), ("protein", "proteomics"), ("cell", "cellular")]:
        assert not _same_stem(a, b), (a, b)
