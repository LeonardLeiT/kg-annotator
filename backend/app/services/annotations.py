import json

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import AnnotationRevision, CanonicalEntity, Document, EntityMention, RelationMention, Sentence
from ..schemas import AnnotationInput


def backfill_annotation_revisions(db: Session) -> int:
    """Import pre-versioning human decisions as revision 1, once per sentence."""
    reviewed = list(db.scalars(
        select(Sentence).where(Sentence.status.in_(["approved", "uncertain", "skipped"]))
    ))
    created = 0
    for sentence in reviewed:
        exists = db.scalar(
            select(func.count()).select_from(AnnotationRevision).where(
                AnnotationRevision.sentence_id == sentence.id
            )
        )
        if exists:
            continue
        mentions = [] if sentence.status == "skipped" else list(db.scalars(
            select(EntityMention).where(EntityMention.sentence_id == sentence.id)
        ))
        mention_ids = {item.id for item in mentions}
        relations = [] if sentence.status == "skipped" else list(db.scalars(
            select(RelationMention).where(RelationMention.sentence_id == sentence.id)
        ))
        entity_payload = [
            {
                "client_id": item.id,
                "text": item.text,
                "entity_type": item.entity_type,
                "start": item.start,
                "end": item.end,
                "context_role": item.context_role,
                "source": "manual",
                "decision": "manual",
            }
            for item in mentions
        ]
        relation_payload = [
            {
                "source_client_id": item.source_mention_id,
                "target_client_id": item.target_mention_id,
                "relation_type": item.relation_type,
                "source": "manual",
            }
            for item in relations
            if item.source_mention_id in mention_ids and item.target_mention_id in mention_ids
        ]
        db.add(AnnotationRevision(
            sentence_id=sentence.id,
            revision_number=1,
            status=sentence.status,
            entities_json=json.dumps(entity_payload, ensure_ascii=False),
            relations_json=json.dumps(relation_payload, ensure_ascii=False),
        ))
        created += 1
    if created:
        db.commit()
    return created


def save_annotation(db: Session, sentence: Sentence, payload: AnnotationInput) -> int:
    existing_rows = list(db.scalars(select(EntityMention).where(EntityMention.sentence_id == sentence.id)))
    existing_ids = [item.id for item in existing_rows]
    old_canonical_ids = {item.canonical_entity_id for item in existing_rows if item.canonical_entity_id}
    if existing_ids:
        db.execute(delete(RelationMention).where(RelationMention.sentence_id == sentence.id))
        db.execute(delete(EntityMention).where(EntityMention.sentence_id == sentence.id))

    # A skipped sentence is an explicit human decision: remove any previous
    # annotation, count it as reviewed, and keep it out of the article KG.
    entities = [] if payload.status == "skipped" else payload.entities
    relations = [] if payload.status == "skipped" else payload.relations

    previous_revision = db.scalar(
        select(func.max(AnnotationRevision.revision_number)).where(
            AnnotationRevision.sentence_id == sentence.id
        )
    ) or 0
    revision_number = previous_revision + 1
    db.add(AnnotationRevision(
        sentence_id=sentence.id,
        revision_number=revision_number,
        status=payload.status,
        entities_json=json.dumps([item.model_dump() for item in entities], ensure_ascii=False),
        relations_json=json.dumps([item.model_dump() for item in relations], ensure_ascii=False),
    ))

    mentions: dict[str, EntityMention] = {}
    for item in entities:
        source_text = {
            "previous": sentence.context_before or "",
            "current": sentence.text,
            "next": sentence.context_after or "",
        }[item.context_role]
        if source_text[item.start:item.end] != item.text:
            raise ValueError(f"实体字符范围与原文不一致: {item.text}")
        canonical = CanonicalEntity(
            preferred_name=item.text,
            entity_type=item.entity_type,
            aliases_json=json.dumps([item.text], ensure_ascii=False),
        )
        db.add(canonical)
        db.flush()
        mention = EntityMention(
            sentence_id=sentence.id,
            text=item.text,
            entity_type=item.entity_type,
            start=item.start,
            end=item.end,
            context_role=item.context_role,
            source=item.source,
            decision=item.decision,
            canonical_entity_id=canonical.id,
        )
        db.add(mention)
        db.flush()
        mentions[item.client_id] = mention

    for item in relations:
        source = mentions.get(item.source_client_id)
        target = mentions.get(item.target_client_id)
        if not source or not target:
            raise ValueError("关系引用了不存在的实体")
        db.add(RelationMention(
            sentence_id=sentence.id,
            source_mention_id=source.id,
            target_mention_id=target.id,
            relation_type=item.relation_type,
            source=item.source,
        ))
    sentence.status = payload.status
    db.flush()
    for canonical_id in old_canonical_ids:
        references = db.scalar(
            select(func.count()).select_from(EntityMention).where(EntityMention.canonical_entity_id == canonical_id)
        )
        if references == 0:
            stale = db.get(CanonicalEntity, canonical_id)
            if stale:
                db.delete(stale)
    remaining = db.scalar(
        select(func.count())
        .select_from(Sentence)
        .where(
            Sentence.document_id == sentence.document_id,
            Sentence.status.not_in(["approved", "uncertain", "skipped"]),
        )
    )
    if remaining == 0:
        document = db.get(Document, sentence.document_id)
        if document:
            document.status = "completed"
    db.commit()
    return revision_number
