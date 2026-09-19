from app.schemas import ExtractionResult, PredictedEntity, PredictedRelation
from app.services.consensus import aggregate_results
from app.services.pipeline import extraction_plan


def result(start: int, end: int, text: str) -> ExtractionResult:
    return ExtractionResult(
        entities=[
            PredictedEntity(local_id="m", text="氧化铝", entity_type="Material", start=0, end=3),
            PredictedEntity(local_id="p", text=text, entity_type="Property", start=start, end=end),
        ],
        relations=[PredictedRelation(source_id="m", target_id="p", relation_type="HAS_PROPERTY")],
    )


def test_three_runs_align_overlapping_entity_boundaries():
    groups, relations = aggregate_results([
        result(8, 13, "断裂韧性"),
        result(5, 13, "较高的断裂韧性"),
        result(8, 13, "断裂韧性"),
    ])

    assert len(groups) == 2
    assert groups[0].votes == 3
    assert groups[1].votes == 3
    assert groups[1].preferred.text == "断裂韧性"
    assert len(relations) == 1
    assert len(relations[0].runs) == 3


def test_extraction_plan_finishes_document_before_next_run():
    assert extraction_plan(["s1", "s2", "s3"], 3) == [
        (1, "s1"), (1, "s2"), (1, "s3"),
        (2, "s1"), (2, "s2"), (2, "s3"),
        (3, "s1"), (3, "s2"), (3, "s3"),
    ]
