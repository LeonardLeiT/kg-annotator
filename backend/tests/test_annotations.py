from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Document, EntityMention, Sentence
from app.schemas import AnnotationInput
from app.services.annotations import save_annotation
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
