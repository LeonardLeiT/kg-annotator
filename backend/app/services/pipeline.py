import json

from sqlalchemy import delete, select

from ..config import get_settings
from ..db import SessionLocal
from ..models import ConsensusEntity, ConsensusRelation, Document, ExtractionRun, Job, Sentence
from ..schemas import ExtractionResult
from .consensus import aggregate_results
from .extraction import get_extractor
from .ontology import load_ontology


def extraction_plan(sentence_ids: list[str], runs: int) -> list[tuple[int, str]]:
    """Build document-level passes: finish every sentence before starting the next run."""
    return [
        (run_index, sentence_id)
        for run_index in range(1, runs + 1)
        for sentence_id in sentence_ids
    ]


def run_document_extraction(job_id: str, document_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        document = db.get(Document, document_id)
        if not job or not document:
            return
        job.status = "running"
        document.status = "extracting"
        db.commit()

        ontology = load_ontology()
        extractor = get_extractor()
        settings = get_settings()
        sentences = list(db.scalars(select(Sentence).where(Sentence.document_id == document_id).order_by(Sentence.ordinal)))
        sentence_ids = [sentence.id for sentence in sentences]
        sentence_by_id = {sentence.id: sentence for sentence in sentences}
        results_by_sentence = {sentence.id: [] for sentence in sentences}

        for sentence in sentences:
            db.execute(delete(ExtractionRun).where(ExtractionRun.sentence_id == sentence.id))
            db.execute(delete(ConsensusRelation).where(ConsensusRelation.sentence_id == sentence.id))
            db.execute(delete(ConsensusEntity).where(ConsensusEntity.sentence_id == sentence.id))
            sentence.status = "extracting"
        db.commit()

        plan = extraction_plan(sentence_ids, settings.extraction_runs)
        failed_calls = 0
        for call_index, (run_index, sentence_id) in enumerate(plan, start=1):
            sentence = sentence_by_id[sentence_id]
            try:
                result = extractor.extract(
                    sentence.text, sentence.context_before, sentence.context_after, ontology, run_index
                )
                results_by_sentence[sentence.id].append(result)
                db.add(ExtractionRun(
                    sentence_id=sentence.id,
                    run_index=run_index,
                    model=extractor.name,
                    raw_output=result.model_dump_json(),
                ))
            except Exception as exc:
                failed_calls += 1
                results_by_sentence[sentence.id].append(ExtractionResult())
                db.add(ExtractionRun(
                    sentence_id=sentence.id,
                    run_index=run_index,
                    model=extractor.name,
                    raw_output=json.dumps({"error": str(exc)}, ensure_ascii=False),
                    status="failed",
                ))
            job.progress = 0.9 * call_index / max(len(plan), 1)
            sentence_position = sentence.ordinal + 1
            job.message = (
                f"第 {run_index}/{settings.extraction_runs} 轮："
                f"已处理 {sentence_position}/{len(sentences)} 个句子"
            )
            db.commit()

        for index, sentence in enumerate(sentences, start=1):
            results = results_by_sentence[sentence.id]
            entity_groups, relation_groups = aggregate_results(results)
            entity_rows: list[ConsensusEntity] = []
            for group in entity_groups:
                preferred = group.preferred
                variants = [
                    {"run": run, **entity.model_dump()} for run, entity in group.members
                ]
                spans = {(entity.start, entity.end) for _, entity in group.members}
                row = ConsensusEntity(
                    sentence_id=sentence.id,
                    text=preferred.text,
                    entity_type=preferred.entity_type,
                    start=preferred.start,
                    end=preferred.end,
                    vote_count=group.votes,
                    boundary_conflict=len(spans) > 1,
                    variants_json=json.dumps(variants, ensure_ascii=False),
                )
                db.add(row)
                entity_rows.append(row)
            db.flush()
            for relation in relation_groups:
                db.add(ConsensusRelation(
                    sentence_id=sentence.id,
                    source_entity_id=entity_rows[relation.source_group].id,
                    target_entity_id=entity_rows[relation.target_group].id,
                    relation_type=relation.relation_type,
                    vote_count=len(relation.runs),
                ))
            sentence.status = "predicted"
            job.progress = 0.9 + 0.1 * index / max(len(sentences), 1)
            job.message = f"正在汇总三轮结果：{index}/{len(sentences)}"
            db.commit()

        document.status = "reviewable"
        job.status = "completed"
        job.progress = 1
        job.message = f"三轮抽取完成；失败调用 {failed_calls}/{len(plan)}"
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        document = db.get(Document, document_id)
        if job:
            job.status = "failed"
            job.message = str(exc)
        if document:
            document.status = "parsed"
        db.commit()
    finally:
        db.close()
