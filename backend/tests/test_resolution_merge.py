import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import CanonicalEntity, Document, EntityMention, MergeCandidate, Sentence
from services.kg.resolution import decide_merge


def make_merge_case(db: Session):
    document = Document(filename="paper.pdf", storage_path="paper.pdf")
    db.add(document)
    db.flush()
    sentence = Sentence(document_id=document.id, ordinal=0, page_number=1, text="alpha beta")
    left = CanonicalEntity(preferred_name="alpha", entity_type="Material", aliases_json='["A"]')
    right = CanonicalEntity(preferred_name="beta", entity_type="Material", aliases_json='["B"]')
    db.add_all([sentence, left, right])
    db.flush()
    db.add(EntityMention(
        sentence_id=sentence.id, text="beta", entity_type="Material", start=6, end=10,
        canonical_entity_id=right.id,
    ))
    candidate = MergeCandidate(
        left_entity_id=left.id, right_entity_id=right.id,
        name_score=.95, context_score=.9, total_score=.935,
    )
    db.add(candidate)
    db.commit()
    return left, right, candidate


def test_manual_merge_requires_name_choice_and_collects_aliases():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        left, right, candidate = make_merge_case(db)
        with pytest.raises(ValueError, match="必须选择"):
            decide_merge(db, candidate, "merge")
        db.rollback()

        decide_merge(db, candidate, "merge", preferred_name="beta")

        assert left.preferred_name == "beta"
        assert right.active is False
        assert set(json.loads(left.aliases_json)) == {"A", "B", "alpha", "beta"}
        mention = db.query(EntityMention).one()
        assert mention.canonical_entity_id == left.id
    engine.dispose()
