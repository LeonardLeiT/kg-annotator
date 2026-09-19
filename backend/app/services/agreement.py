from __future__ import annotations

import json
import random
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ExtractionRun, Sentence
from ..schemas import ExtractionResult
from .consensus import aggregate_results


def fleiss_kappa(category_counts: list[dict[str, int]], annotators: int = 3) -> dict:
    """Fleiss' Kappa for a fixed number of ratings across multiple categories."""
    item_count = len(category_counts)
    if item_count == 0:
        return {"kappa": None, "items": 0, "observed_agreement": None, "expected_agreement": None}
    if any(sum(row.values()) != annotators for row in category_counts):
        raise ValueError("每个候选项的标注数必须等于 annotators")

    categories = set().union(*(row.keys() for row in category_counts))
    observed_per_item = [
        (sum(count * count for count in row.values()) - annotators) / (annotators * (annotators - 1))
        for row in category_counts
    ]
    observed = sum(observed_per_item) / item_count
    category_rates = {
        category: sum(row.get(category, 0) for row in category_counts) / (item_count * annotators)
        for category in categories
    }
    expected = sum(rate * rate for rate in category_rates.values())
    kappa = None if abs(1.0 - expected) < 1e-12 else (observed - expected) / (1.0 - expected)
    return {
        "kappa": round(kappa, 6) if kappa is not None else None,
        "items": item_count,
        "observed_agreement": round(observed, 6),
        "expected_agreement": round(expected, 6),
    }


def fleiss_kappa_binary(vote_counts: list[int], annotators: int = 3) -> dict:
    return fleiss_kappa(
        [{"PRESENT": votes, "NONE": annotators - votes} for votes in vote_counts],
        annotators=annotators,
    )


def agreement_label(kappa: float | None) -> str:
    if kappa is None:
        return "无法计算"
    if kappa < 0:
        return "低于随机一致"
    if kappa < 0.2:
        return "轻微一致"
    if kappa < 0.4:
        return "一般一致"
    if kappa < 0.6:
        return "中等一致"
    if kappa < 0.8:
        return "较强一致"
    return "高度一致"


def document_fleiss_kappa(db: Session, document_id: str, sample_size: int = 50, seed: int = 42) -> dict:
    rows = db.execute(
        select(ExtractionRun, Sentence.ordinal)
        .join(Sentence, Sentence.id == ExtractionRun.sentence_id)
        .where(Sentence.document_id == document_id, ExtractionRun.status == "completed")
        .order_by(Sentence.ordinal, ExtractionRun.run_index)
    ).all()
    by_sentence: dict[str, list[tuple[int, ExtractionResult]]] = defaultdict(list)
    ordinals: dict[str, int] = {}
    for run, ordinal in rows:
        try:
            result = ExtractionResult.model_validate(json.loads(run.raw_output))
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
        by_sentence[run.sentence_id].append((run.run_index, result))
        ordinals[run.sentence_id] = ordinal

    eligible = [
        sentence_id for sentence_id, runs in by_sentence.items()
        if {run_index for run_index, _ in runs} == {1, 2, 3}
    ]
    eligible.sort(key=lambda sentence_id: ordinals[sentence_id])
    selected = random.Random(seed).sample(eligible, min(sample_size, len(eligible))) if eligible else []

    entity_ratings: list[dict[str, int]] = []
    relation_ratings: list[dict[str, int]] = []
    overall_ratings: list[dict[str, int]] = []
    for sentence_id in selected:
        ordered_results = [result for _, result in sorted(by_sentence[sentence_id], key=lambda item: item[0])]
        entity_groups, relation_groups = aggregate_results(ordered_results)
        for group in entity_groups:
            votes = group.votes
            entity_ratings.append({group.preferred.entity_type: votes, "NONE": 3 - votes})
            overall_ratings.append({f"ENTITY:{group.preferred.entity_type}": votes, "NONE": 3 - votes})
        for group in relation_groups:
            votes = len(group.runs)
            relation_ratings.append({group.relation_type: votes, "NONE": 3 - votes})
            overall_ratings.append({f"RELATION:{group.relation_type}": votes, "NONE": 3 - votes})

    entity_metric = fleiss_kappa(entity_ratings)
    relation_metric = fleiss_kappa(relation_ratings)
    overall_metric = fleiss_kappa(overall_ratings)
    for metric in (entity_metric, relation_metric, overall_metric):
        metric["interpretation"] = agreement_label(metric["kappa"])

    return {
        "method": "Fleiss' Kappa",
        "annotators": 3,
        "unit": "实体/关系候选的类型类别；未标注记为 NONE",
        "seed": seed,
        "requested_sample_size": sample_size,
        "eligible_sentences": len(eligible),
        "sampled_sentences": len(selected),
        "sampled_ordinals": sorted(ordinals[sentence_id] + 1 for sentence_id in selected),
        "entity": entity_metric,
        "relation": relation_metric,
        "overall": overall_metric,
    }
