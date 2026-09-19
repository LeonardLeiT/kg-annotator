from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    filename: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    sentence_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sentences: Mapped[list[Sentence]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Sentence(Base):
    __tablename__ = "sentences"
    __table_args__ = (UniqueConstraint("document_id", "ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    context_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    document: Mapped[Document] = relationship(back_populates="sentences")


class FormulaAsset(Base):
    __tablename__ = "formula_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sentence_id: Mapped[str] = mapped_column(ForeignKey("sentences.id"), unique=True, index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    bbox_json: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str] = mapped_column(String(1024))


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (UniqueConstraint("sentence_id", "run_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sentence_id: Mapped[str] = mapped_column(ForeignKey("sentences.id"), index=True)
    run_index: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64), default="v1")
    raw_output: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConsensusEntity(Base):
    __tablename__ = "consensus_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sentence_id: Mapped[str] = mapped_column(ForeignKey("sentences.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(String(128))
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    vote_count: Mapped[int] = mapped_column(Integer)
    boundary_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    type_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    variants_json: Mapped[str] = mapped_column(Text, default="[]")


class ConsensusRelation(Base):
    __tablename__ = "consensus_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sentence_id: Mapped[str] = mapped_column(ForeignKey("sentences.id"), index=True)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("consensus_entities.id"))
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("consensus_entities.id"))
    relation_type: Mapped[str] = mapped_column(String(128))
    vote_count: Mapped[int] = mapped_column(Integer)


class EntityMention(Base):
    __tablename__ = "entity_mentions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sentence_id: Mapped[str] = mapped_column(ForeignKey("sentences.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(String(128))
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    decision: Mapped[str] = mapped_column(String(32), default="accepted")
    canonical_entity_id: Mapped[str | None] = mapped_column(ForeignKey("canonical_entities.id"), nullable=True, index=True)


class RelationMention(Base):
    __tablename__ = "relation_mentions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sentence_id: Mapped[str] = mapped_column(ForeignKey("sentences.id"), index=True)
    source_mention_id: Mapped[str] = mapped_column(ForeignKey("entity_mentions.id"))
    target_mention_id: Mapped[str] = mapped_column(ForeignKey("entity_mentions.id"))
    relation_type: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(32), default="manual")


class AnnotationRevision(Base):
    """Immutable snapshot created every time a sentence annotation is saved."""

    __tablename__ = "annotation_revisions"
    __table_args__ = (UniqueConstraint("sentence_id", "revision_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sentence_id: Mapped[str] = mapped_column(ForeignKey("sentences.id"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    entities_json: Mapped[str] = mapped_column(Text, default="[]")
    relations_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CanonicalEntity(Base):
    __tablename__ = "canonical_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    preferred_name: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MergeCandidate(Base):
    __tablename__ = "merge_candidates"
    __table_args__ = (UniqueConstraint("left_entity_id", "right_entity_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    left_entity_id: Mapped[str] = mapped_column(ForeignKey("canonical_entities.id"), index=True)
    right_entity_id: Mapped[str] = mapped_column(ForeignKey("canonical_entities.id"), index=True)
    name_score: Mapped[float] = mapped_column(Float)
    context_score: Mapped[float] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    reason: Mapped[str] = mapped_column(Text, default="")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
