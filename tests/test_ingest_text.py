from lingua_agent.ingest import normalize_text, segment_paragraphs, segment_sentences


def test_normalize_collapses_inner_whitespace_but_preserves_paragraphs():
    text = "  hello   world  \n\n second   para \n"
    assert normalize_text(text) == "hello world\n\n second para"


def test_paragraph_segmentation():
    text = "para one\nstill one\n\npara two\n\n\npara three"
    paras = segment_paragraphs(text)
    assert paras == ["para one\nstill one", "para two", "para three"]


def test_sentence_segmentation_handles_persian_question_mark():
    # U+061F is the Persian question mark.
    text = "این چیست؟ این یک کتاب است."
    sents = segment_sentences(text)
    assert sents == ["این چیست؟", "این یک کتاب است."]


def test_sentence_segmentation_basic_english():
    text = "Hello world. How are you? Fine!"
    assert segment_sentences(text) == ["Hello world.", "How are you?", "Fine!"]


def test_empty_text():
    assert segment_paragraphs("") == []
    assert segment_sentences("   ") == []
