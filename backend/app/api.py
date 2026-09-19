from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import (
    CanonicalEntity,
    AnnotationRevision,
    Document,
    EntityMention,
    FormulaAsset,
    MergeCandidate,
    RelationMention,
    Sentence,
)
from .schemas import AnnotationInput, MergeDecisionInput
from .services.annotations import save_annotation
from .services.agreement import document_fleiss_kappa
from .services.article_graph import build_article_graph
from .services.documents import is_formula_unit, parse_pdf
from .services.document_deletion import delete_document
from .services.ontology import load_ontology
from .services.graph_export import build_gexf
from .services.resolution import decide_merge, generate_merge_candidates


router = APIRouter(prefix="/api")


def document_json(row: Document) -> dict:
    return {
        "id": row.id, "filename": row.filename, "status": row.status,
        "page_count": row.page_count, "sentence_count": row.sentence_count,
        "created_at": row.created_at,
    }


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ontology")
def ontology():
    item = load_ontology()
    return {"version": item.version, "entity_types": item.entity_types, "relation_types": item.relation_types}


@router.post("/documents")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4()}.pdf"
    target = settings.upload_dir / safe_name
    target.write_bytes(await file.read())
    row = Document(filename=Path(file.filename).name, storage_path=str(target.resolve()))
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        parse_pdf(db, row)
    except Exception as exc:
        row.status = "parse_failed"
        db.commit()
        raise HTTPException(422, f"PDF 解析失败: {exc}") from exc
    return document_json(row)


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return [document_json(item) for item in db.scalars(select(Document).order_by(Document.created_at.desc()))]


@router.delete("/documents/{document_id}")
def remove_document(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "文档不存在")
    if document.status in {"queued", "extracting"}:
        raise HTTPException(409, "文档正在抽取，暂时不能删除")
    result = delete_document(db, document)
    return {"deleted": True, "document_id": document_id, **result}


@router.get("/documents/{document_id}/sentences")
def list_sentences(document_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(Sentence).where(Sentence.document_id == document_id).order_by(Sentence.ordinal))
    return [
        {
            "id": row.id, "ordinal": row.ordinal, "page_number": row.page_number,
            "text": row.text, "status": row.status,
            "content_type": "formula" if is_formula_unit(row.text) else "sentence",
        }
        for row in rows
    ]


@router.get("/documents/{document_id}/graph")
def article_graph(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "文档不存在")
    return build_article_graph(db, document_id)


@router.get("/documents/{document_id}/agreement")
def document_agreement(
    document_id: str,
    sample_size: int = Query(50, ge=1, le=1000),
    seed: int = Query(42, ge=0, le=2_147_483_647),
    annotators: int = Query(2, ge=2, le=100),
    db: Session = Depends(get_db),
):
    if not db.get(Document, document_id):
        raise HTTPException(404, "文档不存在")
    return document_fleiss_kappa(
        db, document_id, sample_size=sample_size, seed=seed, annotators=annotators
    )


@router.get("/sentences/{sentence_id}")
def sentence_detail(sentence_id: str, db: Session = Depends(get_db)):
    sentence = db.get(Sentence, sentence_id)
    if not sentence:
        raise HTTPException(404, "句子不存在")
    mentions = list(db.scalars(select(EntityMention).where(EntityMention.sentence_id == sentence_id)))
    mention_relations = list(db.scalars(select(RelationMention).where(RelationMention.sentence_id == sentence_id)))
    revision_count = db.scalar(
        select(func.count()).select_from(AnnotationRevision).where(
            AnnotationRevision.sentence_id == sentence_id
        )
    )
    formula_asset = db.scalar(select(FormulaAsset).where(FormulaAsset.sentence_id == sentence_id))
    if mentions:
        entity_payload = [
            {
                "id": item.id, "text": item.text, "entity_type": item.entity_type,
                "start": item.start, "end": item.end, "vote_count": 0,
                "boundary_conflict": False, "type_conflict": False, "variants": [],
            }
            for item in mentions
        ]
        relation_payload = [
            {
                "id": item.id, "source_entity_id": item.source_mention_id,
                "target_entity_id": item.target_mention_id, "relation_type": item.relation_type,
                "vote_count": 0,
            }
            for item in mention_relations
        ]
    else:
        entity_payload = []
        relation_payload = []
    return {
        "id": sentence.id,
        "document_id": sentence.document_id,
        "ordinal": sentence.ordinal,
        "page_number": sentence.page_number,
        "text": sentence.text,
        "context_before": sentence.context_before,
        "context_after": sentence.context_after,
        "status": sentence.status,
        "content_type": "formula" if is_formula_unit(sentence.text) else "sentence",
        "has_formula_image": formula_asset is not None,
        "entities": entity_payload,
        "relations": relation_payload,
        "revision_count": revision_count or 0,
    }


@router.get("/sentences/{sentence_id}/formula-image")
def formula_image(sentence_id: str, db: Session = Depends(get_db)):
    asset = db.scalar(select(FormulaAsset).where(FormulaAsset.sentence_id == sentence_id))
    if not asset or not Path(asset.image_path).is_file():
        raise HTTPException(404, "公式原图不存在")
    return FileResponse(asset.image_path, media_type="image/png")


@router.put("/sentences/{sentence_id}/annotation")
def update_annotation(sentence_id: str, payload: AnnotationInput, db: Session = Depends(get_db)):
    sentence = db.get(Sentence, sentence_id)
    if not sentence:
        raise HTTPException(404, "句子不存在")
    try:
        revision = save_annotation(db, sentence, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    return {"status": sentence.status, "revision": revision}


@router.post("/entity-resolution/generate")
def create_merge_candidates(db: Session = Depends(get_db)):
    return generate_merge_candidates(db)


@router.get("/entity-resolution/candidates")
def list_merge_candidates(db: Session = Depends(get_db)):
    rows = db.scalars(select(MergeCandidate).where(MergeCandidate.status.in_(["pending", "deferred"])).order_by(MergeCandidate.total_score.desc()))
    result = []
    for row in rows:
        left = db.get(CanonicalEntity, row.left_entity_id)
        right = db.get(CanonicalEntity, row.right_entity_id)
        if not left or not right:
            continue
        result.append({
            "id": row.id, "status": row.status, "name_score": row.name_score,
            "context_score": row.context_score, "total_score": row.total_score, "reason": row.reason,
            "left": {"id": left.id, "name": left.preferred_name, "type": left.entity_type, "aliases": json.loads(left.aliases_json)},
            "right": {"id": right.id, "name": right.preferred_name, "type": right.entity_type, "aliases": json.loads(right.aliases_json)},
        })
    return result


@router.post("/entity-resolution/candidates/{candidate_id}/{decision}")
def merge_decision(
    candidate_id: str,
    decision: str,
    payload: MergeDecisionInput | None = None,
    db: Session = Depends(get_db),
):
    candidate = db.get(MergeCandidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "候选不存在")
    try:
        decide_merge(db, candidate, decision, preferred_name=payload.preferred_name if payload else None)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    return {"status": candidate.status}


@router.get("/documents/{document_id}/export/jsonl")
def export_jsonl(document_id: str, db: Session = Depends(get_db)):
    sentences = list(db.scalars(select(Sentence).where(Sentence.document_id == document_id).order_by(Sentence.ordinal)))
    lines = []
    for sentence in sentences:
        mentions = list(db.scalars(select(EntityMention).where(EntityMention.sentence_id == sentence.id)))
        relations = list(db.scalars(select(RelationMention).where(RelationMention.sentence_id == sentence.id)))
        lines.append(json.dumps({
            "sentence_id": sentence.id, "page": sentence.page_number, "text": sentence.text,
            "entities": [{"id": e.id, "text": e.text, "type": e.entity_type, "start": e.start, "end": e.end, "canonical_id": e.canonical_entity_id} for e in mentions],
            "relations": [{"source": r.source_mention_id, "type": r.relation_type, "target": r.target_mention_id} for r in relations],
        }, ensure_ascii=False))
    return StreamingResponse(iter(["\n".join(lines)]), media_type="application/x-ndjson", headers={"Content-Disposition": "attachment; filename=annotations.jsonl"})


@router.get("/documents/{document_id}/export/csv")
def export_csv(document_id: str, db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["document_id", "sentence_id", "page", "subject", "relation", "object", "evidence"])
    rows = db.execute(
        select(RelationMention, Sentence)
        .join(Sentence, Sentence.id == RelationMention.sentence_id)
        .where(Sentence.document_id == document_id)
    )
    for relation, sentence in rows:
        source = db.get(EntityMention, relation.source_mention_id)
        target = db.get(EntityMention, relation.target_mention_id)
        writer.writerow([document_id, sentence.id, sentence.page_number, source.text, relation.relation_type, target.text, sentence.text])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=triples.csv"})


@router.get("/documents/{document_id}/export/gexf")
def export_gexf(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "文档不存在")
    content = build_gexf(build_article_graph(db, document_id))
    return Response(
        content=content,
        media_type="application/gexf+xml",
        headers={"Content-Disposition": 'attachment; filename="article-kg.gexf"'},
    )
