from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AnnotationRevision,
    CanonicalEntity,
    Document,
    EntityMention,
    FormulaAsset,
    MergeCandidate,
    RelationMention,
    Sentence,
)


def delete_document(db: Session, document: Document) -> dict[str, int]:
    """Delete one document and its private data while preserving shared entities."""
    sentence_ids = list(
        db.scalars(select(Sentence.id).where(Sentence.document_id == document.id))
    )
    files = [Path(document.storage_path)]
    parse_asset_dir = Path(document.storage_path).parent / "parse_assets" / document.id

    if sentence_ids:
        files.extend(
            Path(path)
            for path in db.scalars(
                select(FormulaAsset.image_path).where(FormulaAsset.sentence_id.in_(sentence_ids))
            )
        )
        mention_ids = list(
            db.scalars(select(EntityMention.id).where(EntityMention.sentence_id.in_(sentence_ids)))
        )
        touched_canonical_ids = set(
            db.scalars(
                select(EntityMention.canonical_entity_id).where(
                    EntityMention.sentence_id.in_(sentence_ids),
                    EntityMention.canonical_entity_id.is_not(None),
                )
            )
        )

        if mention_ids:
            db.execute(
                delete(RelationMention).where(
                    or_(
                        RelationMention.sentence_id.in_(sentence_ids),
                        RelationMention.source_mention_id.in_(mention_ids),
                        RelationMention.target_mention_id.in_(mention_ids),
                    )
                )
            )

        db.execute(delete(FormulaAsset).where(FormulaAsset.sentence_id.in_(sentence_ids)))
        db.execute(delete(AnnotationRevision).where(AnnotationRevision.sentence_id.in_(sentence_ids)))
        db.execute(delete(EntityMention).where(EntityMention.sentence_id.in_(sentence_ids)))
        db.execute(delete(Sentence).where(Sentence.id.in_(sentence_ids)))
        db.flush()

        if touched_canonical_ids:
            still_referenced = set(
                db.scalars(
                    select(EntityMention.canonical_entity_id).where(
                        EntityMention.canonical_entity_id.in_(touched_canonical_ids)
                    )
                )
            )
            orphan_ids = touched_canonical_ids - still_referenced
            if orphan_ids:
                db.execute(
                    delete(MergeCandidate).where(
                        or_(
                            MergeCandidate.left_entity_id.in_(orphan_ids),
                            MergeCandidate.right_entity_id.in_(orphan_ids),
                        )
                    )
                )
                db.execute(delete(CanonicalEntity).where(CanonicalEntity.id.in_(orphan_ids)))
    else:
        orphan_ids = set()

    db.execute(delete(Document).where(Document.id == document.id))
    db.commit()

    removed_files = 0
    for path in dict.fromkeys(files):
        try:
            if path.is_file():
                path.unlink()
                removed_files += 1
        except OSError:
            # The database deletion is authoritative; a locked artifact can be
            # cleaned manually later without leaving broken database records.
            continue

    try:
        if parse_asset_dir.is_dir():
            shutil.rmtree(parse_asset_dir)
    except OSError:
        pass

    return {
        "sentences_deleted": len(sentence_ids),
        "canonical_entities_deleted": len(orphan_ids),
        "files_deleted": removed_files,
    }
