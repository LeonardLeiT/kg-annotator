from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import EntityMention, RelationMention, Sentence


def normalize_entity_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"[\s_\-–—]+", "", value)


def build_article_graph(db: Session, document_id: str) -> dict:
    sentences = list(db.scalars(
        select(Sentence)
        .where(Sentence.document_id == document_id)
        .order_by(Sentence.ordinal)
    ))
    approved = [sentence for sentence in sentences if sentence.status == "approved"]
    skipped = [sentence for sentence in sentences if sentence.status == "skipped"]
    reviewed = [sentence for sentence in sentences if sentence.status in {"approved", "uncertain", "skipped"}]
    sentence_ids = [sentence.id for sentence in approved]
    sentence_by_id = {sentence.id: sentence for sentence in approved}
    if not sentence_ids:
        return {
            "stats": {
                "sentences": len(sentences), "reviewed": len(reviewed),
                "approved": 0, "skipped": len(skipped), "nodes": 0, "edges": 0,
            },
            "nodes": [], "edges": [],
        }

    mentions = list(db.scalars(
        select(EntityMention).where(EntityMention.sentence_id.in_(sentence_ids))
    ))
    relations = list(db.scalars(
        select(RelationMention).where(RelationMention.sentence_id.in_(sentence_ids))
    ))

    grouped_mentions: dict[tuple[str, str], list[EntityMention]] = defaultdict(list)
    mention_to_key: dict[str, tuple[str, str]] = {}
    for mention in mentions:
        key = (mention.entity_type, normalize_entity_name(mention.text))
        grouped_mentions[key].append(mention)
        mention_to_key[mention.id] = key

    nodes = []
    key_to_id: dict[tuple[str, str], str] = {}
    for key, members in grouped_mentions.items():
        node_id = members[0].canonical_entity_id or members[0].id
        key_to_id[key] = node_id
        aliases = sorted({member.text for member in members}, key=lambda value: (len(value), value))
        evidence = [
            {
                "sentence_id": member.sentence_id,
                "page": sentence_by_id[member.sentence_id].page_number,
                "text": {
                    "previous": sentence_by_id[member.sentence_id].context_before,
                    "current": sentence_by_id[member.sentence_id].text,
                    "next": sentence_by_id[member.sentence_id].context_after,
                }.get(member.context_role) or sentence_by_id[member.sentence_id].text,
                "context_role": member.context_role,
            }
            for member in members
        ]
        nodes.append({
            "id": node_id,
            "name": aliases[0],
            "entity_type": key[0],
            "aliases": aliases,
            "mention_count": len(members),
            "evidence": evidence,
        })

    grouped_edges: dict[tuple[str, str, str], list[RelationMention]] = defaultdict(list)
    for relation in relations:
        source_key = mention_to_key.get(relation.source_mention_id)
        target_key = mention_to_key.get(relation.target_mention_id)
        if not source_key or not target_key:
            continue
        grouped_edges[(key_to_id[source_key], relation.relation_type, key_to_id[target_key])].append(relation)

    edges = []
    for (source_id, relation_type, target_id), members in grouped_edges.items():
        evidence = [
            {
                "sentence_id": member.sentence_id,
                "page": sentence_by_id[member.sentence_id].page_number,
                "text": sentence_by_id[member.sentence_id].text,
            }
            for member in members
        ]
        edges.append({
            "source_id": source_id,
            "relation_type": relation_type,
            "target_id": target_id,
            "evidence_count": len(members),
            "evidence": evidence,
        })

    return {
        "stats": {
            "sentences": len(sentences), "reviewed": len(reviewed),
            "approved": len(approved), "skipped": len(skipped),
            "nodes": len(nodes), "edges": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }
