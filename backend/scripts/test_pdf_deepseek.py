from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path

import pymupdf


def configure_deepseek() -> None:
    key = getpass.getpass("DeepSeek API key: ")
    if not key:
        raise SystemExit("API key is required")
    os.environ["DEEPSEEK_API_KEY"] = key
    os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
    os.environ["LLM_MODEL"] = "deepseek-flash"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small three-pass DeepSeek extraction test on a PDF")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("data/deepseek_test_results.json"))
    args = parser.parse_args()

    configure_deepseek()

    from app.config import get_settings
    get_settings.cache_clear()
    from app.services.consensus import aggregate_results
    from app.services.documents import extract_page_sentences
    from app.services.extraction import get_extractor
    from app.services.ontology import load_ontology

    page_sentences: list[tuple[int, str]] = []
    with pymupdf.open(args.pdf) as pdf:
        for page_index, page in enumerate(pdf, start=1):
            page_sentences.extend((page_index, text) for text in extract_page_sentences(page))

    keywords = (
        "thermal stability", "free energy", "Schwarz", "grain boundar",
        "coherent twin", "Kelvin", "Voronoi",
    )
    candidates = [
        (index, page, text)
        for index, (page, text) in enumerate(page_sentences)
        if 70 <= len(text) <= 650
        and not text.casefold().startswith(("keywords:", "free energy criterion for", "figure "))
        and any(keyword.casefold() in text.casefold() for keyword in keywords)
        and any(token in f" {text.casefold()} " for token in (" is ", " are ", " has ", " have ", " provides ", " establishes ", " imposes ", " demonstrates ", " consists ", " shows "))
    ]
    candidates.sort(
        key=lambda item: (
            -sum(keyword.casefold() in item[2].casefold() for keyword in keywords),
            item[0],
        )
    )
    selected = sorted(candidates[: args.limit], key=lambda item: item[0])
    if not selected:
        raise SystemExit("No suitable sentences found")

    ontology = load_ontology()
    extractor = get_extractor()
    report: dict = {
        "pdf": str(args.pdf.resolve()),
        "model": extractor.name,
        "configured_model": get_settings().llm_model,
        "runs_per_sentence": args.runs,
        "sentences": [],
    }

    results_by_selection = [[] for _ in selected]
    errors_by_selection = [[] for _ in selected]
    for run_index in range(1, args.runs + 1):
        print(f"starting document pass {run_index}/{args.runs}", flush=True)
        for selection_index, (source_index, _page, sentence) in enumerate(selected, start=1):
            before = page_sentences[source_index - 1][1] if source_index > 0 else None
            after = page_sentences[source_index + 1][1] if source_index + 1 < len(page_sentences) else None
            print(f"pass {run_index}/{args.runs}, sentence {selection_index}/{len(selected)}", flush=True)
            try:
                results_by_selection[selection_index - 1].append(
                    extractor.extract(sentence, before, after, ontology, run_index)
                )
            except Exception as exc:  # keep partial test evidence
                errors_by_selection[selection_index - 1].append({"run": run_index, "error": str(exc)})

    for selection_index, (_source_index, page, sentence) in enumerate(selected, start=1):
        results = results_by_selection[selection_index - 1]
        errors = errors_by_selection[selection_index - 1]
        entity_groups, relation_groups = aggregate_results(results)
        entities = []
        for group_index, group in enumerate(entity_groups):
            preferred = group.preferred
            entities.append({
                "group_index": group_index,
                "text": preferred.text,
                "entity_type": preferred.entity_type,
                "start": preferred.start,
                "end": preferred.end,
                "votes": group.votes,
                "variants": [
                    {"run": run, **entity.model_dump()} for run, entity in group.members
                ],
            })
        relations = [
            {
                "source_group": relation.source_group,
                "source_text": entities[relation.source_group]["text"],
                "relation_type": relation.relation_type,
                "target_group": relation.target_group,
                "target_text": entities[relation.target_group]["text"],
                "votes": len(relation.runs),
            }
            for relation in relation_groups
        ]
        report["sentences"].append({
            "page": page,
            "text": sentence,
            "successful_runs": len(results),
            "errors": errors,
            "entities": entities,
            "relations": relations,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {args.output.resolve()}")


if __name__ == "__main__":
    main()
