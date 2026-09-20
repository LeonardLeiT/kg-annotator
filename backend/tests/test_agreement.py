import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import AnnotationRevision, Document, Sentence
from services.evaluation.agreement import agreement_label, document_fleiss_kappa, fleiss_kappa, fleiss_kappa_binary


def test_fleiss_kappa_is_one_for_mixed_unanimous_items():
    metric = fleiss_kappa_binary([3, 3, 0, 0])
    assert metric["kappa"] == 1.0
    assert metric["observed_agreement"] == 1.0
    assert metric["expected_agreement"] == 0.5


def test_fleiss_kappa_handles_no_candidate_items():
    metric = fleiss_kappa_binary([])
    assert metric["kappa"] is None
    assert metric["items"] == 0
    assert agreement_label(metric["kappa"]) == "无法计算"


def test_multicategory_kappa_represents_unanimous_types():
    metric = fleiss_kappa([{"Material": 3}, {"Property": 3}, {"NONE": 3}])
    assert metric["kappa"] == 1.0
    assert metric["items"] == 3


def test_document_agreement_uses_manual_revisions_and_requested_version_count():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        document = Document(filename="paper.pdf", storage_path="paper.pdf")
        db.add(document)
        db.flush()
        sentence = Sentence(document_id=document.id, ordinal=0, page_number=1, text="Quartz")
        db.add(sentence)
        db.flush()
        entity = [{
            "client_id": "q", "text": "Quartz", "entity_type": "Material",
            "start": 0, "end": 6, "source": "manual", "decision": "manual",
        }]
        for number in range(1, 4):
            db.add(AnnotationRevision(
                sentence_id=sentence.id, revision_number=number, status="approved",
                entities_json=json.dumps(entity), relations_json="[]",
            ))
        db.commit()

        result = document_fleiss_kappa(db, document.id, annotators=3)
        assert result["annotators"] == 3
        assert result["eligible_sentences"] == 1
        assert result["entity"]["observed_agreement"] == 1.0
    engine.dispose()
