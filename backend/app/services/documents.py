import json
import re
from pathlib import Path

import pymupdf
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import Document, FormulaAsset, Sentence


SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+(?=[A-Z0-9])")
EQUATION_NUMBER = re.compile(r"^\(?\s*(?:\d+|[A-Za-z]\d*)\s*\)?$")
MATH_MARKS = re.compile(r"[=<>≤≥≈≃≡+−–*/×÷^_∑∏∫∂√∞±∇∆ΔλμσπωαβγθφψχΩ]")
STRONG_MATH_MARKS = re.compile(r"[=<>≤≥≈≃≡∑∏∫∂√∞±∇∆ΔλμσπωαβγθφψχΩ]")
LATEX_MARKS = re.compile(r"\\(?:frac|sum|int|partial|sqrt|Delta|lambda|mu|sigma|omega|alpha|beta|gamma)\b")


def split_sentences(text: str) -> list[str]:
    normalized = text.replace("\u00a0", " ").replace("\r\n", "\n")
    normalized = re.sub(r"(?<=[A-Za-z])-[ \t]*\n[ \t]*(?=[a-z])", "", normalized)
    normalized = re.sub(r"[ \t]*\n[ \t]*", " ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized).strip()
    normalized = re.sub(
        r"([.!?])(\d+(?:[−\-–,]\d+)*)\s+(?=[A-Z])",
        lambda match: f"{match.group(1)}{match.group(2)}\u241e",
        normalized,
    )
    parts: list[str] = []
    for citation_segment in normalized.split("\u241e"):
        parts.extend(item.strip() for item in SENTENCE_BOUNDARY.split(citation_segment) if item.strip())
    return parts


def is_equation_number(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped and len(stripped) <= 10 and EQUATION_NUMBER.fullmatch(stripped))


def is_formula_unit(text: str) -> bool:
    """Conservative heuristic for display equations extracted from PDF lines."""
    stripped = text.strip()
    if not stripped or is_equation_number(stripped) or len(stripped) > 500:
        return False
    math_marks = len(MATH_MARKS.findall(stripped))
    strong_math_marks = len(STRONG_MATH_MARKS.findall(stripped))
    substantive = len(re.findall(r"[A-Za-z0-9\u0370-\u03ff\u4e00-\u9fff]", stripped))
    prose_words = re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,}", stripped)
    has_relation = bool(re.search(r"[=≤≥≈≃≡<>]", stripped))
    has_latex = bool(LATEX_MARKS.search(stripped))
    has_equation_label = bool(re.search(r"\(\s*\d+[a-zA-Z]?\s*\)\s*$", stripped))
    prose_probe = re.sub(r"\b(?:w\s+h\s+e\s+r\s+e|a\s+s)\b", lambda match: match.group(0).replace(" ", ""), stripped.lower())
    if re.search(r"\b(?:where|depends|determined|shown|figure|represents)\b", prose_probe):
        return False
    if has_relation:
        sides = re.split(r"[=≤≥≈≃≡<>]", stripped, maxsplit=1)
        if len(sides) != 2 or not re.search(r"[A-Za-z0-9\u0370-\u03ff]", sides[0]) or not re.search(r"[A-Za-z0-9\u0370-\u03ff]", sides[1]):
            return False
    return (
        substantive >= 2
        and (
        has_latex
        or (has_relation and len(prose_words) <= 10)
        or (strong_math_marks >= 1 and math_marks >= 2 and len(prose_words) <= 5)
        or (has_equation_label and math_marks >= 1)
        )
    )


def split_block_units(block_text: str) -> list[str]:
    """Split prose into sentences while preserving consecutive display-equation lines."""
    raw_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in block_text.replace("\r\n", "\n").split("\n")]
    lines = [line for line in raw_lines if line]
    units: list[str] = []
    prose_lines: list[str] = []
    formula_lines: list[str] = []

    def flush_prose() -> None:
        if prose_lines:
            units.extend(split_sentences("\n".join(prose_lines)))
            prose_lines.clear()

    def flush_formula() -> None:
        if formula_lines:
            units.append("\n".join(formula_lines))
            formula_lines.clear()

    for line in lines:
        if is_formula_unit(line):
            flush_prose()
            formula_lines.append(line)
        elif is_equation_number(line) and formula_lines:
            formula_lines.append(line)
        else:
            flush_formula()
            prose_lines.append(line)
    flush_formula()
    flush_prose()
    return units


def _math_span(span: dict) -> bool:
    text = span.get("text", "").strip()
    font = span.get("font", "").lower()
    if not text:
        return True
    if text.lower() in {"as", "in", "of", "to", "is", "at", "on", "by", "or", "where", "depends"}:
        return False
    if "italic" in font or "stix" in font:
        return True
    if float(span.get("size", 99)) <= 8 and len(text) <= 4:
        return True
    if text in {"ln", "log", "exp", "sin", "cos", "tan", "d"}:
        return True
    return bool(re.fullmatch(r"(?:[A-Za-z]{1,2}|\d+(?:\.\d+)?|[(),.\[\]{}+−–=*/×÷^_<>≤≥≈≃≡±]+)", text))


def _join_formula_spans(spans: list[dict]) -> str:
    ordered = sorted(spans, key=lambda item: (item["bbox"][0], item["bbox"][1]))
    tokens: list[str] = []
    index = 0
    while index < len(ordered):
        current = ordered[index]
        if index + 1 < len(ordered):
            following = ordered[index + 1]
            current_text = current.get("text", "").strip()
            following_text = following.get("text", "").strip()
            same_x = abs(current["bbox"][0] - following["bbox"][0]) <= 1.5
            vertically_separate = current["bbox"][3] <= following["bbox"][1] + 0.5
            if same_x and vertically_separate and current_text.isdigit() and following_text.isdigit():
                tokens.append(f"({current_text}/{following_text})")
                index += 2
                continue
        tokens.append(current.get("text", ""))
        index += 1
    text = "".join(tokens)
    text = re.split(r"(?:,?\s+where\b|,?\s+as\s+)", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"([=≤≥≈≃≡<>])", r" \1 ", text)
    return re.sub(r"\s+", " ", text).strip(" ,")


def _equation_records(spans: list[dict], page_width: float) -> list[tuple[dict, str, tuple[float, float, float, float]]]:
    """Return the equality span and its coordinate-rebuilt expression."""
    equations: list[tuple[dict, str, tuple[float, float, float, float]]] = []
    equation_texts: set[str] = set()
    seen_operators: set[tuple[int, int]] = set()
    for operator in spans:
        if not re.search(r"[=≤≥≈≃≡]", operator.get("text", "")):
            continue
        ox0, oy0, ox1, oy1 = operator["bbox"]
        marker = (round(ox0), round(oy0))
        if marker in seen_operators:
            continue
        seen_operators.add(marker)
        operator_mid_y = (oy0 + oy1) / 2
        left_edge, right_edge = (0, page_width / 2) if ox0 < page_width / 2 else (page_width / 2, page_width)
        band = [
            span for span in spans
            if left_edge <= span["bbox"][0] < right_edge
            and abs(((span["bbox"][1] + span["bbox"][3]) / 2) - operator_mid_y) <= 7.5
        ]
        ordered = sorted(band, key=lambda item: (item["bbox"][0], item["bbox"][1]))
        try:
            operator_index = ordered.index(operator)
        except ValueError:
            continue
        start = operator_index
        while start > 0 and _math_span(ordered[start - 1]) and ordered[start]["bbox"][0] - ordered[start - 1]["bbox"][2] < 18:
            start -= 1
        end = operator_index + 1
        while end < len(ordered) and _math_span(ordered[end]) and ordered[end]["bbox"][0] - ordered[end - 1]["bbox"][2] < 18:
            end += 1
        formula = _join_formula_spans(ordered[start:end])
        if is_formula_unit(formula) and formula not in equation_texts:
            members = ordered[start:end]
            bbox = (
                min(item["bbox"][0] for item in members),
                min(item["bbox"][1] for item in members),
                max(item["bbox"][2] for item in members),
                max(item["bbox"][3] for item in members),
            )
            equations.append((operator, formula, bbox))
            equation_texts.add(formula)
    return equations


def extract_block_equations(block: dict, page_width: float) -> list[str]:
    """Rebuild equations whose glyphs PyMuPDF split across several baselines."""
    spans = [span for line in block.get("lines", []) for span in line.get("spans", []) if span.get("text")]
    return [formula for _operator, formula, _bbox in _equation_records(spans, page_width)]


def extract_page_units(page: pymupdf.Page) -> list[tuple[str, tuple[float, float, float, float] | None]]:
    units_with_bbox: list[tuple[str, tuple[float, float, float, float] | None]] = []
    page_dict = page.get_text("dict", sort=True)
    text_blocks = [block for block in page_dict.get("blocks", []) if block.get("type") == 0]
    page_spans = [span for block in text_blocks for line in block.get("lines", []) for span in line.get("spans", []) if span.get("text")]
    page_equations = _equation_records(page_spans, page.rect.width)
    for block in text_blocks:
        block_spans = [span for line in block.get("lines", []) for span in line.get("spans", []) if span.get("text")]
        block_text = "\n".join(
            "".join(span.get("text", "") for span in line.get("spans", []))
            for line in block.get("lines", [])
        )
        if block_text.strip():
            units = split_block_units(block_text)
            rebuilt_equations = [
                (formula, bbox) for operator, formula, bbox in page_equations
                if any(operator is span for span in block_spans)
            ]
            # Discard isolated operator debris when a coordinate-rebuilt equation
            # is available, then keep the reconstructed expression as one unit.
            if rebuilt_equations:
                units = [unit for unit in units if not re.fullmatch(r"[=≤≥≈≃≡+−–*/×÷\s]+", unit)]
            units_with_bbox.extend((unit, None) for unit in units)
            units_with_bbox.extend((formula, bbox) for formula, bbox in rebuilt_equations if formula not in units)
    return units_with_bbox


def extract_page_sentences(page: pymupdf.Page) -> list[str]:
    return [text for text, _bbox in extract_page_units(page)]


def surrounding_context(rows: list[Sentence], index: int) -> tuple[str | None, str | None]:
    """Give equations the nearest narrative explanation on both sides."""
    if not is_formula_unit(rows[index].text):
        return (
            rows[index - 1].text if index > 0 else None,
            rows[index + 1].text if index + 1 < len(rows) else None,
        )

    before = next(
        (rows[i].text for i in range(index - 1, -1, -1) if not is_formula_unit(rows[i].text)),
        None,
    )
    after = next(
        (rows[i].text for i in range(index + 1, len(rows)) if not is_formula_unit(rows[i].text)),
        None,
    )
    return before, after


def parse_pdf(db: Session, document: Document) -> Document:
    pages: list[tuple[int, str, tuple[float, float, float, float] | None, str | None]] = []
    formula_dir = Path(document.storage_path).parent / "formula_assets"
    formula_dir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(Path(document.storage_path)) as pdf:
        page_count = len(pdf)
        for page_index, page in enumerate(pdf):
            for sentence_text, bbox in extract_page_units(page):
                image_path = None
                if bbox is not None:
                    padding = 5
                    clip = pymupdf.Rect(bbox) + (-padding, -padding, padding, padding)
                    clip &= page.rect
                    image_path = str((formula_dir / f"{document.id}_{len(pages)}.png").resolve())
                    page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip, alpha=False).save(image_path)
                pages.append((page_index + 1, sentence_text, bbox, image_path))

    old_sentence_ids = list(db.scalars(select(Sentence.id).where(Sentence.document_id == document.id)))
    if old_sentence_ids:
        db.execute(delete(FormulaAsset).where(FormulaAsset.sentence_id.in_(old_sentence_ids)))
    db.execute(delete(Sentence).where(Sentence.document_id == document.id))
    rows: list[Sentence] = []
    ordinal = 0
    formula_metadata: list[tuple[Sentence, tuple[float, float, float, float], str]] = []
    for page_number, sentence_text, bbox, image_path in pages:
        row = Sentence(
            document_id=document.id,
            ordinal=ordinal,
            page_number=page_number,
            text=sentence_text,
        )
        rows.append(row)
        if bbox is not None and image_path is not None:
            formula_metadata.append((row, bbox, image_path))
        ordinal += 1

    for index, row in enumerate(rows):
        row.context_before, row.context_after = surrounding_context(rows, index)
        db.add(row)
    db.flush()
    for row, bbox, image_path in formula_metadata:
        db.add(FormulaAsset(
            sentence_id=row.id,
            page_number=row.page_number,
            bbox_json=json.dumps(bbox),
            image_path=image_path,
        ))

    document.page_count = page_count
    document.sentence_count = len(rows)
    document.status = "parsed"
    db.commit()
    db.refresh(document)
    return document
