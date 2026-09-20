from services.document.document_structure import (
    StructuredBlock,
    blocks_from_mineru_markdown,
    blocks_from_mineru_v2,
    clean_markdown_content,
    identify_references,
    merge_incomplete_blocks,
    render_clean_markdown,
    write_clean_artifacts,
)


def test_mineru_v2_preserves_inline_and_display_latex_with_page_numbers():
    payload = [
        [
            {
                "type": "page_header",
                "content": {"page_header_content": [{"type": "text", "content": "Journal"}]},
            },
            {
                "type": "paragraph",
                "bbox": [100, 200, 900, 260],
                "content": {
                    "paragraph_content": [
                        {"type": "text", "content": "The entropy is "},
                        {"type": "equation_inline", "content": "S=-\\frac{\\partial F}{\\partial T}"},
                        {"type": "text", "content": "."},
                    ]
                },
            },
        ],
        [
            {
                "type": "interline_equation",
                "bbox": [250, 300, 750, 380],
                "content": {"type": "equation", "content": "G=E-TS"},
            }
        ],
    ]

    blocks = blocks_from_mineru_v2(payload)

    assert blocks[0].page_number == 1
    assert blocks[0].text == "The entropy is $S=-\\frac{\\partial F}{\\partial T}$."
    assert blocks[1] == StructuredBlock(
        page_number=2,
        category="equation",
        text="$$G=E-TS$$",
        bbox=(250.0, 300.0, 750.0, 380.0),
    )


def test_structure_cleaning_stops_at_references_and_ignores_figures():
    payload = [[
        {"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": "Body sentence."}]}},
        {"type": "image", "content": {"image_caption": [{"type": "text", "content": "Figure 1. Noise"}]}},
        {"type": "title", "content": {"title_content": [{"type": "text", "content": "References"}]}},
        {"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": "[1] Hidden reference."}]}},
    ]]

    assert [block.text for block in blocks_from_mineru_v2(payload)] == ["Body sentence."]
    assert identify_references("# Bibliography")
    assert clean_markdown_content("A<details>noise</details>\n\n\nB") == "A\n\nB"


def test_incomplete_paragraphs_merge_and_dehyphenate_across_pages():
    blocks = [
        StructuredBlock(1, "main_text", "Thermal sta-"),
        StructuredBlock(2, "main_text", "bility improves."),
        StructuredBlock(2, "main_text", "A complete sentence."),
    ]
    assert merge_incomplete_blocks(blocks) == [
        StructuredBlock(1, "main_text", "Thermal stability improves."),
        StructuredBlock(2, "main_text", "A complete sentence."),
    ]


def test_clean_pipeline_writes_structure_json_and_final_markdown(tmp_path):
    raw = [
        StructuredBlock(1, "heading", "A Scientific Paper"),
        StructuredBlock(1, "abstract", "ABSTRACT: A concise summary."),
        StructuredBlock(1, "main_text", "A paragraph split across"),
        StructuredBlock(2, "main_text", "two pages."),
        StructuredBlock(2, "equation", "$$G=E-TS$$", (200, 300, 800, 380)),
    ]
    cleaned = merge_incomplete_blocks(raw)

    markdown_path = write_clean_artifacts(raw, cleaned, tmp_path)

    assert markdown_path.read_text(encoding="utf-8") == (
        "# A Scientific Paper\n\n"
        "## Abstract\n\n"
        "A concise summary.\n\n"
        "A paragraph split across two pages.\n\n"
        "$$G=E-TS$$\n"
    )
    assert (tmp_path / "clean" / "label_structure.json").is_file()
    assert (tmp_path / "clean" / "label_structure_cleaned.json").is_file()
    assert render_clean_markdown(cleaned).count("G=E-TS") == 1


def test_legacy_full_markdown_uses_same_clean_pipeline():
    markdown = """# Paper title

ABSTRACT: Summary text.

Body text with $G=E-TS$.

![](images/figure.jpg)

Figure 1. A caption.

# References

[1] A reference that must be excluded.
"""

    blocks = blocks_from_mineru_markdown(markdown)
    clean = render_clean_markdown(blocks)

    assert clean.startswith("# Paper title")
    assert "## Abstract\n\nSummary text." in clean
    assert "$G=E-TS$" in clean
    assert "figure.jpg" not in clean
    assert "A reference" not in clean
