from app.models import Sentence
from app.schemas import ExtractionResult, PredictedEntity, PredictedRelation
from services.kg.ontology import Ontology
from services.kg.suggestions import suggest_sentence


class FakeExtractor:
    name = "test-llm"

    def extract(self, sentence, context_before, context_after, ontology, run_index):
        assert sentence == "氧化铝具有较高硬度。"
        assert context_before == "前文"
        assert context_after == "后文"
        assert run_index == 1
        assert "Material" in ontology.entity_types
        return ExtractionResult(
            entities=[
                PredictedEntity(local_id="e1", text="氧化铝", entity_type="Material", start=0, end=3),
                PredictedEntity(local_id="e2", text="硬度", entity_type="Property", start=7, end=9),
            ],
            relations=[
                PredictedRelation(source_id="e1", relation_type="HAS_PROPERTY", target_id="e2")
            ],
        )


def test_suggestion_is_transient_structured_result():
    sentence = Sentence(
        document_id="doc",
        ordinal=0,
        page_number=1,
        text="氧化铝具有较高硬度。",
        context_before="前文",
        context_after="后文",
    )
    ontology = Ontology(
        version="test",
        entity_types={"Material": {}, "Property": {}},
        relation_types={"HAS_PROPERTY": {}},
    )

    result = suggest_sentence(sentence, extractor=FakeExtractor(), ontology=ontology)

    assert result.model == "test-llm"
    assert [item.text for item in result.entities] == ["氧化铝", "硬度"]
    assert result.relations[0].relation_type == "HAS_PROPERTY"
