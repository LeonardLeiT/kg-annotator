from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    CanonicalEntity,
    Document,
    EntityMention,
    FormulaAsset,
    MergeCandidate,
    RelationMention,
    Sentence,
)
from services.document.document_deletion import delete_document


def test_delete_document_removes_private_data_and_preserves_shared_entity(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    pdf_one = tmp_path / "one.pdf"
    pdf_two = tmp_path / "two.pdf"
    formula_image = tmp_path / "formula.png"
    for path in (pdf_one, pdf_two, formula_image):
        path.write_bytes(b"test")

    with Session(engine) as db:
        first = Document(filename="one.pdf", storage_path=str(pdf_one), status="reviewable")
        second = Document(filename="two.pdf", storage_path=str(pdf_two), status="reviewable")
        db.add_all([first, second])
        db.flush()
        first_sentence = Sentence(document_id=first.id, ordinal=0, page_number=1, text="A B")
        second_sentence = Sentence(document_id=second.id, ordinal=0, page_number=1, text="A")
        db.add_all([first_sentence, second_sentence])
        db.flush()

        shared = CanonicalEntity(preferred_name="A", entity_type="Material")
        orphan = CanonicalEntity(preferred_name="B", entity_type="Material")
        db.add_all([shared, orphan])
        db.flush()
        first_shared = EntityMention(
            sentence_id=first_sentence.id, text="A", entity_type="Material", start=0, end=1,
            canonical_entity_id=shared.id,
        )
        first_orphan = EntityMention(
            sentence_id=first_sentence.id, text="B", entity_type="Material", start=2, end=3,
            canonical_entity_id=orphan.id,
        )
        second_shared = EntityMention(
            sentence_id=second_sentence.id, text="A", entity_type="Material", start=0, end=1,
            canonical_entity_id=shared.id,
        )
        db.add_all([first_shared, first_orphan, second_shared])
        db.flush()
        db.add(RelationMention(
            sentence_id=first_sentence.id, source_mention_id=first_shared.id,
            target_mention_id=first_orphan.id, relation_type="related_to",
        ))
        db.add(FormulaAsset(
            sentence_id=first_sentence.id, page_number=1,
            bbox_json="[]", image_path=str(formula_image),
        ))
        db.add(MergeCandidate(
            left_entity_id=shared.id, right_entity_id=orphan.id,
            name_score=.9, context_score=.9, total_score=.9,
        ))
        db.commit()

        first_id = first.id
        first_sentence_id = first_sentence.id
        shared_id = shared.id
        orphan_id = orphan.id
        result = delete_document(db, first)

        assert result["sentences_deleted"] == 1
        assert result["canonical_entities_deleted"] == 1
        assert db.get(Document, first_id) is None
        assert db.get(Sentence, first_sentence_id) is None
        assert db.get(CanonicalEntity, orphan_id) is None
        assert db.get(CanonicalEntity, shared_id) is not None
        assert db.scalar(select(MergeCandidate)) is None
        assert not pdf_one.exists()
        assert not formula_image.exists()
        assert pdf_two.exists()
