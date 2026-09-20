from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SKIPPED_BLOCK_TYPES = {
    "page_header",
    "page_footer",
    "page_number",
    "page_aside_text",
    "header",
    "footer",
    "aside_text",
    "image",
    "chart",
    "table",
}
REFERENCE_HEADER = re.compile(
    r"^\s*#{0,6}\s*(?:references|bibliography)(?:\s+and\s+notes?)?\s*:?\s*$",
    re.IGNORECASE,
)
METADATA_LINE = re.compile(
    r"^\s*(?:received|revised|accepted|published)\s*:\s*|"
    r"^\s*(?:https?://)?(?:dx\.)?doi\.org/|"
    r"^\s*downloaded\s+via\b",
    re.IGNORECASE,
)
FRONT_MATTER_NOISE = re.compile(
    r"^\s*(?:keywords?|cite\s+this|read\s+online|access|metrics\s*&\s*more|"
    r"article\s+recommendations?|supporting\s+information)\b",
    re.IGNORECASE,
)
SENTENCE_END = re.compile(r"(?:[.!?。！？；;]|[.!?][\]\)\"']|\$)\s*(?:\d+(?:[,\-−–]\d+)*)?\s*$")


@dataclass(frozen=True)
class StructuredBlock:
    page_number: int
    category: str
    text: str
    bbox: tuple[float, float, float, float] | None = None


def clean_markdown_content(text: str) -> str:
    """Remove MinerU presentation artifacts without touching LaTeX."""
    text = re.sub(r"<details>.*?</details>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<summary>.*?</summary>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("\ufffd", "-").replace("\u00a0", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk_markdown_by_blank_lines(text: str) -> list[str]:
    chunks: list[str] = []
    buffer: list[str] = []
    for line in text.splitlines():
        if line.strip():
            buffer.append(line)
        elif buffer:
            chunks.append("\n".join(buffer).strip())
            buffer = []
    if buffer:
        chunks.append("\n".join(buffer).strip())
    return chunks


def identify_references(text: str) -> bool:
    if REFERENCE_HEADER.match(text):
        return True
    entries = re.findall(r"^\s*[\*†‡§¶#]*\s*\[\d+\]\s+", text, re.MULTILINE)
    return len(entries) >= 3 and text.count("\n") >= 2


def _render_node(node: Any) -> str:
    if isinstance(node, list):
        return "".join(_render_node(item) for item in node)
    if not isinstance(node, dict):
        return ""

    node_type = str(node.get("type", ""))
    content = node.get("content")
    if node_type == "equation_inline" and isinstance(content, str):
        return f" ${content.strip()}$ "
    if node_type in {"equation", "interline_equation", "display_equation"} and isinstance(content, str):
        return f"$${content.strip()}$$"
    if node_type == "text" and isinstance(content, str):
        return content
    if isinstance(content, str):
        return content
    if content is not None:
        rendered = _render_node(content)
        if rendered:
            return rendered
    return "".join(_render_node(value) for key, value in node.items() if key not in {"bbox", "type"})


def _block_text(block: dict[str, Any]) -> str:
    block_type = str(block.get("type", ""))
    content = block.get("content", {})
    if block_type in {"equation", "interline_equation", "display_equation"}:
        raw = _render_node(content).strip()
        return raw if raw.startswith("$$") else f"$${raw}$$" if raw else ""
    rendered = re.sub(r"[ \t]+", " ", _render_node(content).strip())
    return re.sub(r"\s+([,.;:!?。！？；])", r"\1", rendered)


def _bbox(block: dict[str, Any]) -> tuple[float, float, float, float] | None:
    value = block.get("bbox")
    if isinstance(value, list) and len(value) == 4:
        try:
            return tuple(float(item) for item in value)  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None
    return None


def _category(block_type: str, text: str) -> str:
    if block_type == "title" or text.lstrip().startswith("#"):
        return "heading"
    if block_type in {"equation", "interline_equation", "display_equation"}:
        return "equation"
    if re.fullmatch(r"\s*(?:\$\$.+\$\$|\$[^$]{10,}\$)\s*", text, re.DOTALL):
        return "equation"
    if re.match(r"^\s*abstract\s*:?", text, re.IGNORECASE):
        return "abstract"
    return "main_text"


def blocks_from_mineru_v2(
    payload: list[Any], *, merge: bool = True
) -> list[StructuredBlock]:
    """Convert MinerU content_list_v2 into page-aware, LaTeX-preserving blocks."""
    result: list[StructuredBlock] = []
    references_started = False
    seen_title = False
    seen_body = False
    for page_index, page in enumerate(payload):
        if not isinstance(page, list):
            continue
        for raw_block in page:
            if not isinstance(raw_block, dict):
                continue
            block_type = str(raw_block.get("type", ""))
            if block_type in SKIPPED_BLOCK_TYPES:
                continue
            text = clean_markdown_content(_block_text(raw_block))
            if not text or METADATA_LINE.search(text):
                continue
            if block_type == "title":
                seen_title = True
            elif not seen_title and (
                "doi.org" in text.lower()
                or re.search(r"\bjournal\b|(?:https?://|www\.|\b\w+\.\w+\.\w+/)", text, re.IGNORECASE)
                or (
                    block_type not in {"equation", "interline_equation", "display_equation"}
                    and len(text) < 30
                    and not re.search(r"[.!?。！？]", text)
                )
            ):
                continue
            if FRONT_MATTER_NOISE.match(text):
                continue
            if identify_references(text):
                references_started = True
            if references_started:
                continue
            if (
                block_type != "title"
                and seen_title
                and not seen_body
                and len(text) < 200
                and not re.search(r"[.!?。！？]", text)
            ):
                # Author/affiliation and publisher controls between title and abstract.
                continue
            category = _category(block_type, text)
            if category in {"abstract", "main_text"} and len(text) >= 100:
                seen_body = True
            result.append(StructuredBlock(
                page_number=page_index + 1,
                category=category,
                text=text,
                bbox=_bbox(raw_block),
            ))
    return merge_incomplete_blocks(result) if merge else result


def blocks_from_mineru_v1(
    payload: list[Any], *, merge: bool = True
) -> list[StructuredBlock]:
    """Compatibility path for older flat MinerU content_list.json files."""
    result: list[StructuredBlock] = []
    references_started = False
    for raw_block in payload:
        if not isinstance(raw_block, dict):
            continue
        block_type = str(raw_block.get("type", ""))
        if block_type in SKIPPED_BLOCK_TYPES:
            continue
        text = clean_markdown_content(str(raw_block.get("text", "")))
        if not text or METADATA_LINE.search(text):
            continue
        if identify_references(text):
            references_started = True
        if references_started:
            continue
        result.append(StructuredBlock(
            page_number=int(raw_block.get("page_idx", 0)) + 1,
            category=_category(block_type, text),
            text=text,
            bbox=_bbox(raw_block),
        ))
    return merge_incomplete_blocks(result) if merge else result


def blocks_from_mineru_markdown(
    markdown: str, *, merge: bool = True
) -> list[StructuredBlock]:
    """Clean legacy MinerU full.md output using the same structural pipeline."""
    result: list[StructuredBlock] = []
    references_started = False
    for chunk in chunk_markdown_by_blank_lines(clean_markdown_content(markdown)):
        text = chunk.strip()
        if not text or METADATA_LINE.search(text) or FRONT_MATTER_NOISE.match(text):
            continue
        if identify_references(text):
            references_started = True
        if references_started:
            continue
        if re.search(r"!\[[^]]*\]\([^)]+\)|<table\b", text, re.IGNORECASE):
            continue
        if re.match(r"^\s*(?:fig(?:ure)?\.?|table)\s*\d+\b", text, re.IGNORECASE):
            continue
        block_type = "title" if text.startswith("#") else "paragraph"
        result.append(StructuredBlock(
            page_number=1,
            category=_category(block_type, text),
            text=text,
        ))
    return merge_incomplete_blocks(result) if merge else result


def merge_incomplete_blocks(blocks: list[StructuredBlock]) -> list[StructuredBlock]:
    """Join paragraph fragments using SCI4RAG's sentence-aware merge strategy."""
    merged: list[StructuredBlock] = []
    pending: StructuredBlock | None = None
    for block in blocks:
        if block.category in {"heading", "equation"}:
            if pending:
                merged.append(pending)
                pending = None
            merged.append(block)
            continue
        if pending:
            joiner = "" if re.search(r"[A-Za-z]-\s*$", pending.text) else " "
            left = re.sub(r"(?<=[A-Za-z])-\s*$", "", pending.text)
            block = StructuredBlock(
                page_number=pending.page_number,
                category=pending.category,
                text=(left + joiner + block.text).strip(),
                bbox=pending.bbox,
            )
            pending = None
        if SENTENCE_END.search(block.text):
            merged.append(block)
        else:
            pending = block
    if pending:
        merged.append(pending)
    return merged


def render_clean_markdown(blocks: list[StructuredBlock]) -> str:
    """Render the final clean paper used by the annotation pipeline."""
    output: list[str] = []
    title_written = False
    abstract_written = False
    for block in blocks:
        text = clean_markdown_content(block.text)
        if not text:
            continue
        if block.category == "heading":
            heading = re.sub(r"^#+\s*", "", text).strip()
            if not heading:
                continue
            output.append(f"# {heading}" if not title_written else f"## {heading}")
            title_written = True
            continue
        if block.category == "abstract":
            abstract = re.sub(r"^\s*abstract\s*:?\s*", "", text, flags=re.IGNORECASE)
            if not abstract_written:
                output.extend(["## Abstract", abstract])
                abstract_written = True
            else:
                output.append(abstract)
            continue
        if block.category in {"main_text", "equation"}:
            output.append(text)
    return "\n\n".join(output).strip() + "\n"


def _block_payload(block: StructuredBlock) -> dict[str, Any]:
    return {
        "page_number": block.page_number,
        "category": block.category,
        "content": block.text,
        "bbox": list(block.bbox) if block.bbox is not None else None,
    }


def write_clean_artifacts(
    raw_blocks: list[StructuredBlock],
    cleaned_blocks: list[StructuredBlock],
    output_dir: Path,
) -> Path:
    """Persist SCI4RAG-style intermediate structures and the final clean Markdown."""
    clean_dir = output_dir / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    (clean_dir / "label_structure.json").write_text(
        json.dumps([_block_payload(block) for block in raw_blocks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (clean_dir / "label_structure_cleaned.json").write_text(
        json.dumps([_block_payload(block) for block in cleaned_blocks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path = clean_dir / "document.md"
    markdown_path.write_text(render_clean_markdown(cleaned_blocks), encoding="utf-8")
    return markdown_path
