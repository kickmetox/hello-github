from app.search_engine import TfidfIndex, snippet, tokenize


def test_stopwords_are_removed():
    assert tokenize("Der Vertrag und the invoice") == ["vertrag", "invoice"]


def test_rare_term_ranks_the_specific_document_first():
    engine = TfidfIndex()
    engine.rebuild([
        (1, "apfel birne apfel birne " + "alpha " * 30),
        (2, "apfel kirsche"),
        (3, "zeta zeta zeta zeta"),
    ])
    birne = engine.search("birne")
    assert birne[0][0] == 1
    assert all(doc_id != 2 for doc_id, _score in birne)
    zeta = engine.search("zeta")
    assert zeta[0][0] == 3
    assert zeta[0][1] <= 1


def test_repeated_term_outranks_a_single_mention():
    engine = TfidfIndex()
    engine.rebuild([
        (1, "alpha " * 40 + " zeta"),
        (2, "zeta zeta zeta zeta"),
    ])
    ranked = engine.search("zeta")
    assert [doc_id for doc_id, _score in ranked] == [2, 1]
    assert ranked[0][1] > ranked[1][1]


def test_snippet_marks_the_matching_region():
    text = "Einleitung. " + ("wort " * 40) + "Kündigung des Mietvertrags folgt."
    chunk = snippet(text, "Kündigung Mietvertrag", radius=30)
    assert "Kündigung" in chunk
    assert chunk.startswith("…")
