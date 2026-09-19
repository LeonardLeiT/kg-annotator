from __future__ import annotations

import json
import random
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AnnotationRevision, Sentence


def fleiss_kappa(category_counts: list[dict[str, int]], annotators: int = 3) -> dict:
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
        [{"PRESENT": votes, "NONE": annotators - votes} for votes in vote_counts], annotators
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


def _revision_ratings(revisions: list[AnnotationRevision]) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    parsed: list[tuple[dict[tuple, str], dict[tuple, str]]] = []
    for revision in revisions:
        entities = json.loads(revision.entities_json)
        relations = json.loads(revision.relations_json)
        by_client = {item["client_id"]: item for item in entities}
        entity_map = {
            (item.get("context_role", "current"), item["start"], item["end"], item["text"]): item["entity_type"] for item in entities
        }
        relation_map: dict[tuple, str] = {}
        for relation in relations:
            source = by_client.get(relation["source_client_id"])
            target = by_client.get(relation["target_client_id"])
            if source and target:
                source_key = (source.get("context_role", "current"), source["start"], source["end"], source["text"])
                target_key = (target.get("context_role", "current"), target["start"], target["end"], target["text"])
                relation_map[(source_key, target_key)] = relation["relation_type"]
        parsed.append((entity_map, relation_map))

    entity_keys = set().union(*(set(items) for items, _ in parsed))
    relation_keys = set().union(*(set(items) for _, items in parsed))
    entity_ratings = [dict(Counter(items.get(key, "NONE") for items, _ in parsed)) for key in entity_keys]
    relation_ratings = [dict(Counter(items.get(key, "NONE") for _, items in parsed)) for key in relation_keys]
    return entity_ratings, relation_ratings


def document_fleiss_kappa(
    db: Session,
    document_id: str,
    sample_size: int = 50,
    seed: int = 42,
    annotators: int = 2,
) -> dict:
    rows = db.execute(
        select(AnnotationRevision, Sentence.ordinal)
        .join(Sentence, Sentence.id == AnnotationRevision.sentence_id)
        .where(Sentence.document_id == document_id)
        .order_by(Sentence.ordinal, AnnotationRevision.revision_number)
    ).all()
    by_sentence: dict[str, list[AnnotationRevision]] = defaultdict(list)
    ordinals: dict[str, int] = {}
    for revision, ordinal in rows:
        by_sentence[revision.sentence_id].append(revision)
        ordinals[revision.sentence_id] = ordinal

    eligible = sorted(
        (sentence_id for sentence_id, revisions in by_sentence.items() if len(revisions) >= annotators),
        key=lambda sentence_id: ordinals[sentence_id],
    )
    selected = random.Random(seed).sample(eligible, min(sample_size, len(eligible))) if eligible else []
    entity_ratings: list[dict[str, int]] = []
    relation_ratings: list[dict[str, int]] = []
    for sentence_id in selected:
        entity_rows, relation_rows = _revision_ratings(by_sentence[sentence_id][-annotators:])
        entity_ratings.extend(entity_rows)
        relation_ratings.extend(relation_rows)

    metrics = [
        fleiss_kappa(entity_ratings, annotators),
        fleiss_kappa(relation_ratings, annotators),
        fleiss_kappa(entity_ratings + relation_ratings, annotators),
    ]
    for metric in metrics:
        metric["interpretation"] = agreement_label(metric["kappa"])
    return {
        "method": "Fleiss' Kappa",
        "annotators": annotators,
        "unit": "人工标注版本中的实体/关系候选类别；未标注记为 NONE",
        "seed": seed,
        "requested_sample_size": sample_size,
        "eligible_sentences": len(eligible),
        "sampled_sentences": len(selected),
        "sampled_ordinals": sorted(ordinals[sentence_id] + 1 for sentence_id in selected),
        "entity": metrics[0],
        "relation": metrics[1],
        "overall": metrics[2],
    }
