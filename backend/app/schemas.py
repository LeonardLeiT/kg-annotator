from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PredictedEntity(BaseModel):
    local_id: str
    text: str
    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class PredictedRelation(BaseModel):
    source_id: str
    relation_type: str
    target_id: str
    evidence: str = ""


class ExtractionResult(BaseModel):
    entities: list[PredictedEntity] = Field(default_factory=list)
    relations: list[PredictedRelation] = Field(default_factory=list)


class EntityInput(BaseModel):
    client_id: str
    text: str
    entity_type: str
    start: int
    end: int
    source: Literal["manual"] = "manual"
    decision: Literal["manual"] = "manual"


class RelationInput(BaseModel):
    source_client_id: str
    relation_type: str
    target_client_id: str
    source: Literal["manual"] = "manual"


class AnnotationInput(BaseModel):
    status: Literal["approved", "uncertain", "skipped"] = "approved"
    entities: list[EntityInput] = Field(default_factory=list)
    relations: list[RelationInput] = Field(default_factory=list)


class MergeDecisionInput(BaseModel):
    preferred_name: str | None = None
