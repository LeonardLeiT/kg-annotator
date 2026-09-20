from __future__ import annotations

import json
import math
import re

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models import CanonicalEntity, EntityMention, MergeCandidate, Sentence
from app.config import get_settings
from .embeddings import get_embedding_provider


def normalize_name(value: str) -> str:
    return re.sub(r"[\s\-_（）()]+", "", value).casefold()


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def context_for(db: Session, entity_id: str) -> str:
    rows = db.execute(
        select(Sentence.text)
        .join(EntityMention, EntityMention.sentence_id == Sentence.id)
        .where(EntityMention.canonical_entity_id == entity_id)
        .limit(5)
    ).scalars()
    return " ".join(rows)


def classify_similarity(score: float, auto_threshold: float = 0.99, candidate_threshold: float = 0.85) -> str:
    if score >= auto_threshold:
        return "auto_merge"
    if score >= candidate_threshold:
        return "candidate"
    return "ignore"


def _merge_entities(
    db: Session,
    left: CanonicalEntity,
    right: CanonicalEntity,
    preferred_name: str | None = None,
) -> None:
    aliases = set(json.loads(left.aliases_json or "[]"))
    aliases.update(json.loads(right.aliases_json or "[]"))
    aliases.add(left.preferred_name)
    aliases.add(right.preferred_name)
    if preferred_name:
        left.preferred_name = preferred_name
        aliases.add(preferred_name)
    left.aliases_json = json.dumps(sorted(aliases), ensure_ascii=False)
    db.execute(
        EntityMention.__table__.update()
        .where(EntityMention.canonical_entity_id == right.id)
        .values(canonical_entity_id=left.id)
    )
    right.active = False


def generate_merge_candidates(db: Session) -> dict[str, int]:
    settings = get_settings()
    auto_threshold = settings.embedding_auto_merge_threshold
    candidate_threshold = settings.embedding_candidate_threshold
    if not 0 <= candidate_threshold <= auto_threshold <= 1:
        raise ValueError("实体合并阈值必须满足 0 <= candidate <= auto <= 1")

    db.execute(delete(MergeCandidate).where(MergeCandidate.status.in_(["pending", "deferred", "superseded"])))
    rejected_pairs = {
        tuple(sorted((item.left_entity_id, item.right_entity_id)))
        for item in db.scalars(select(MergeCandidate).where(MergeCandidate.status == "rejected"))
    }
    entities = list(db.scalars(select(CanonicalEntity).where(CanonicalEntity.active.is_(True))))
    provider = get_embedding_provider()
    contexts = [context_for(db, entity.id) or entity.preferred_name for entity in entities]
    name_vectors = provider.embed_documents([entity.preferred_name for entity in entities]) if entities else []
    context_vectors = provider.embed_documents(contexts) if entities else []
    scored_pairs: list[tuple[float, float, float, CanonicalEntity, CanonicalEntity]] = []
    for left_index, left in enumerate(entities):
        for right_index in range(left_index + 1, len(entities)):
            right = entities[right_index]
            if left.entity_type != right.entity_type:
                continue
            if tuple(sorted((left.id, right.id))) in rejected_pairs:
                continue
            name_score = cosine(name_vectors[left_index], name_vectors[right_index])
            context_score = cosine(context_vectors[left_index], context_vectors[right_index])
            total = 0.7 * name_score + 0.3 * context_score
            if normalize_name(left.preferred_name) == normalize_name(right.preferred_name):
                total = 1.0
            if classify_similarity(total, auto_threshold, candidate_threshold) == "ignore":
                continue
            scored_pairs.append((total, name_score, context_score, left, right))

    auto_merged = 0
    candidates = 0
    for total, name_score, context_score, left, right in sorted(scored_pairs, key=lambda item: item[0], reverse=True):
        if not left.active or not right.active:
            continue
        similarity_policy = classify_similarity(total, auto_threshold, candidate_threshold)
        names_are_identical = left.preferred_name == right.preferred_name
        policy = "auto_merge" if similarity_policy == "auto_merge" and names_are_identical else "candidate"
        status = "auto_merged" if policy == "auto_merge" else "pending"
        candidate = MergeCandidate(
            left_entity_id=left.id,
            right_entity_id=right.id,
            name_score=name_score,
            context_score=context_score,
            total_score=total,
            status=status,
            reason=(
                f"名称完全相同且综合相似度 {total:.2%}，自动合并"
                if policy == "auto_merge"
                else (
                    f"综合相似度 {total:.2%}，但名称不同，需人工选择合并后的规范名称"
                    if similarity_policy == "auto_merge"
                    else f"综合相似度 {total:.2%}，达到 {candidate_threshold:.0%} 人工审核阈值"
                )
            ),
        )
        db.add(candidate)
        if policy == "auto_merge":
            _merge_entities(db, left, right)
            auto_merged += 1
        else:
            candidates += 1
    db.commit()
    return {"auto_merged": auto_merged, "candidates": candidates, "pairs_scored": len(scored_pairs)}


def decide_merge(
    db: Session,
    candidate: MergeCandidate,
    decision: str,
    preferred_name: str | None = None,
) -> None:
    if decision == "reject":
        candidate.status = "rejected"
        db.commit()
        return
    if decision == "defer":
        candidate.status = "deferred"
        db.commit()
        return
    if decision != "merge":
        raise ValueError("未知合并决定")

    left = db.get(CanonicalEntity, candidate.left_entity_id)
    right = db.get(CanonicalEntity, candidate.right_entity_id)
    if not left or not right or not left.active or not right.active:
        raise ValueError("实体不存在或已经被合并")
    allowed_names = {left.preferred_name, right.preferred_name}
    if left.preferred_name != right.preferred_name:
        if not preferred_name:
            raise ValueError("名称不同的实体合并时必须选择合并后的规范名称")
        if preferred_name not in allowed_names:
            raise ValueError("规范名称必须从待合并实体的名称中选择")
    _merge_entities(db, left, right, preferred_name=preferred_name or left.preferred_name)
    candidate.status = "merged"
    other_candidates = db.scalars(select(MergeCandidate).where(
        MergeCandidate.id != candidate.id,
        MergeCandidate.status == "pending",
        or_(
            MergeCandidate.left_entity_id == right.id,
            MergeCandidate.right_entity_id == right.id,
        ),
    ))
    for item in other_candidates:
        item.status = "superseded"
    db.commit()
