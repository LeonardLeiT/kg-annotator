from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import AnnotationRevision, Document, EntityMention, Sentence
from app.schemas import AnnotationInput, EntityInput
from app.services.annotations import backfill_annotation_revisions, save_annotation
from app.services.article_graph import build_article_graph
from app.services.graph_export import GEXF_NS, build_gexf
from xml.etree import ElementTree as ET


def test_skipped_sentence_is_reviewed_but_excluded_from_graph():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as db:
        document = Document(filename="paper.pdf", storage_path="paper.pdf", status="reviewable")
        db.add(document)
        db.flush()
        sentence = Sentence(
            document_id=document.id,
            ordinal=0,
            page_number=1,
            text="This sentence is not relevant.",
            status="predicted",
        )
        db.add(sentence)
        db.commit()

        save_annotation(db, sentence, AnnotationInput(status="skipped"))

        assert sentence.status == "skipped"
        assert document.status == "completed"
        assert list(db.scalars(select(EntityMention))) == []
        graph = build_article_graph(db, document.id)
        assert graph["stats"] == {
            "sentences": 1,
            "reviewed": 1,
            "approved": 0,
            "skipped": 1,
            "nodes": 0,
            "edges": 0,
        }
    engine.dispose()


def test_gexf_export_preserves_graph_attributes():
    graph = {
        "nodes": [{
            "id": "n1", "name": "Alumina & MgO", "entity_type": "Material",
            "aliases": ["Alumina", "Al₂O₃"], "mention_count": 2,
        }],
        "edges": [{
            "source_id": "n1", "target_id": "n1", "relation_type": "RELATED_TO",
            "evidence_count": 3,
        }],
    }
    root = ET.fromstring(build_gexf(graph))
    node = root.find(f".//{{{GEXF_NS}}}node")
    edge = root.find(f".//{{{GEXF_NS}}}edge")
    assert node is not None and node.attrib["label"] == "Alumina & MgO"
    assert edge is not None and edge.attrib["label"] == "RELATED_TO"
    assert edge.attrib["weight"] == "3"


def test_each_manual_save_creates_an_immutable_revision_and_updates_latest_graph():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        document = Document(filename="paper.pdf", storage_path="paper.pdf", status="reviewable")
        db.add(document)
        db.flush()
        sentence = Sentence(document_id=document.id, ordinal=0, page_number=1, text="Quartz is stable.")
        db.add(sentence)
        db.commit()

        first = AnnotationInput(entities=[EntityInput(
            client_id="q", text="Quartz", entity_type="Material", start=0, end=6
        )])
        assert save_annotation(db, sentence, first) == 1
        second = AnnotationInput(entities=[EntityInput(
            client_id="q2", text="Quartz", entity_type="Mineral", start=0, end=6
        )])
        assert save_annotation(db, sentence, second) == 2

        revisions = list(db.scalars(select(AnnotationRevision).order_by(AnnotationRevision.revision_number)))
        assert [item.revision_number for item in revisions] == [1, 2]
        assert '"Material"' in revisions[0].entities_json
        assert '"Mineral"' in revisions[1].entities_json
        latest = db.scalar(select(EntityMention))
        assert latest is not None and latest.entity_type == "Mineral"
    engine.dispose()


def test_existing_human_decisions_are_backfilled_once():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        document = Document(filename="paper.pdf", storage_path="paper.pdf")
        db.add(document)
        db.flush()
        approved = Sentence(
            document_id=document.id, ordinal=0, page_number=1, text="Quartz", status="approved"
        )
        skipped = Sentence(
            document_id=document.id, ordinal=1, page_number=1, text="References", status="skipped"
        )
        db.add_all([approved, skipped])
        db.flush()
        db.add(EntityMention(
            sentence_id=approved.id, text="Quartz", entity_type="Material",
            start=0, end=6, source="manual", decision="manual",
        ))
        db.commit()

        assert backfill_annotation_revisions(db) == 2
        assert backfill_annotation_revisions(db) == 0
        revisions = list(db.scalars(select(AnnotationRevision).order_by(AnnotationRevision.sentence_id)))
        assert len(revisions) == 2
        approved_revision = next(item for item in revisions if item.sentence_id == approved.id)
        skipped_revision = next(item for item in revisions if item.sentence_id == skipped.id)
        assert '"Quartz"' in approved_revision.entities_json
        assert skipped_revision.entities_json == "[]"
    engine.dispose()
