from app.models import Sentence
from services.document.documents import is_formula_unit, split_block_units, split_sentences, surrounding_context


def test_split_chinese_and_english_sentences():
    text = "氧化铝具有较高硬度。它也有良好的韧性！\nA sample was heated. Results improved."
    assert split_sentences(text) == [
        "氧化铝具有较高硬度。",
        "它也有良好的韧性！",
        "A sample was heated.",
        "Results improved.",
    ]


def test_join_wrapped_pdf_lines_and_dehyphenate():
    text = "The thermal sta-\nbility of Schwarz nanocrystals is high.\nFree energy decreases."
    assert split_sentences(text) == [
        "The thermal stability of Schwarz nanocrystals is high.",
        "Free energy decreases.",
    ]


def test_split_sentence_after_numeric_citation():
    assert split_sentences("This aligns with observations.20 This preference supports stability.") == [
        "This aligns with observations.20",
        "This preference supports stability.",
    ]


def test_preserve_multiline_display_formula_as_one_unit():
    block = "The free energy is written as:\nG = E - TS\n+ γ A\n(1)\nwhere E is the internal energy."
    assert split_block_units(block) == [
        "The free energy is written as:",
        "G = E - TS\n+ γ A\n(1)",
        "where E is the internal energy.",
    ]
    assert is_formula_unit("G = E - TS\n+ γ A\n(1)")


def test_formula_context_uses_nearest_narrative_on_both_sides():
    rows = [
        Sentence(text="The following equation defines free energy."),
        Sentence(text="G = E - TS"),
        Sentence(text="F = U - TS"),
        Sentence(text="Here T denotes temperature."),
    ]
    assert surrounding_context(rows, 1) == (
        "The following equation defines free energy.",
        "Here T denotes temperature.",
    )
