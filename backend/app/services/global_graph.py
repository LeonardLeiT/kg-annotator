from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CanonicalEntity, Document, EntityMention, RelationMention, Sentence


def _evidence_text(sentence: Sentence, mention: EntityMention) -> str:
    return {
        "previous": sentence.context_before,
        "current": sentence.text,
        "next": sentence.context_after,
    }.get(mention.context_role) or sentence.text


def build_global_graph(db: Session) -> dict:
    """Aggregate every approved annotation into one canonical cross-document KG."""
    rows = db.execute(
        select(Sentence, Document)
        .join(Document, Document.id == Sentence.document_id)
        .where(Sentence.status == "approved")
        .order_by(Document.created_at, Sentence.ordinal)
    ).all()
    sentence_by_id = {sentence.id: sentence for sentence, _ in rows}
    document_by_sentence = {sentence.id: document for sentence, document in rows}
    sentence_ids = list(sentence_by_id)
    mentions = list(db.scalars(
        select(EntityMention).where(EntityMention.sentence_id.in_(sentence_ids))
    )) if sentence_ids else []
    relations = list(db.scalars(
        select(RelationMention).where(RelationMention.sentence_id.in_(sentence_ids))
    )) if sentence_ids else []

    canonical_ids = {item.canonical_entity_id for item in mentions if item.canonical_entity_id}
    canonicals = {
        item.id: item for item in db.scalars(
            select(CanonicalEntity).where(CanonicalEntity.id.in_(canonical_ids))
        )
    } if canonical_ids else {}

    grouped: dict[str, list[EntityMention]] = defaultdict(list)
    mention_to_node: dict[str, str] = {}
    for mention in mentions:
        node_id = mention.canonical_entity_id or mention.id
        grouped[node_id].append(mention)
        mention_to_node[mention.id] = node_id

    nodes = []
    for node_id, members in grouped.items():
        canonical = canonicals.get(node_id)
        aliases = {member.text for member in members}
        if canonical:
            aliases.update(json.loads(canonical.aliases_json or "[]"))
            aliases.add(canonical.preferred_name)
        documents = {document_by_sentence[member.sentence_id].id for member in members}
        evidence = [
            {
                "document_id": document_by_sentence[member.sentence_id].id,
                "document": document_by_sentence[member.sentence_id].filename,
                "sentence_id": member.sentence_id,
                "page": sentence_by_id[member.sentence_id].page_number,
                "text": _evidence_text(sentence_by_id[member.sentence_id], member),
                "context_role": member.context_role,
            }
            for member in members
        ]
        nodes.append({
            "id": node_id,
            "name": canonical.preferred_name if canonical else members[0].text,
            "entity_type": canonical.entity_type if canonical else members[0].entity_type,
            "aliases": sorted(aliases, key=lambda value: (len(value), value)),
            "mention_count": len(members),
            "document_count": len(documents),
            "evidence": evidence,
        })

    grouped_edges: dict[tuple[str, str, str], list[RelationMention]] = defaultdict(list)
    for relation in relations:
        source_id = mention_to_node.get(relation.source_mention_id)
        target_id = mention_to_node.get(relation.target_mention_id)
        if source_id and target_id:
            grouped_edges[(source_id, relation.relation_type, target_id)].append(relation)

    edges = []
    for (source_id, relation_type, target_id), members in grouped_edges.items():
        evidence = [
            {
                "document_id": document_by_sentence[item.sentence_id].id,
                "document": document_by_sentence[item.sentence_id].filename,
                "sentence_id": item.sentence_id,
                "page": sentence_by_id[item.sentence_id].page_number,
                "text": sentence_by_id[item.sentence_id].text,
            }
            for item in members
        ]
        edges.append({
            "source_id": source_id,
            "relation_type": relation_type,
            "target_id": target_id,
            "evidence_count": len(members),
            "document_count": len({item["document_id"] for item in evidence}),
            "evidence": evidence,
        })

    all_documents = list(db.scalars(select(Document)))
    all_sentences = list(db.scalars(select(Sentence)))
    return {
        "scope": "global",
        "stats": {
            "documents": len(all_documents),
            "sentences": len(all_sentences),
            "reviewed": sum(item.status in {"approved", "uncertain", "skipped"} for item in all_sentences),
            "approved": len(rows),
            "skipped": sum(item.status == "skipped" for item in all_sentences),
            "nodes": len(nodes),
            "edges": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }
