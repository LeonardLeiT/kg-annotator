from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from jinja2 import Template
from ..config import get_settings
from ..schemas import ExtractionResult, PredictedEntity, PredictedRelation
from .ontology import Ontology


class TripleExtractor(Protocol):
    name: str

    def extract(
        self,
        sentence: str,
        context_before: str | None,
        context_after: str | None,
        ontology: Ontology,
        run_index: int,
    ) -> ExtractionResult: ...


def validate_result(result: ExtractionResult, sentence: str, ontology: Ontology) -> ExtractionResult:
    valid_entities: list[PredictedEntity] = []
    valid_ids: set[str] = set()
    for entity in result.entities:
        start, end = entity.start, entity.end
        if sentence[start:end] != entity.text:
            occurrences = [m.start() for m in re.finditer(re.escape(entity.text), sentence)]
            if len(occurrences) != 1:
                continue
            start = occurrences[0]
            end = start + len(entity.text)
        if entity.entity_type not in ontology.entity_types:
            continue
        fixed = entity.model_copy(update={"start": start, "end": end})
        valid_entities.append(fixed)
        valid_ids.add(fixed.local_id)

    valid_relations = [
        relation
        for relation in result.relations
        if relation.source_id in valid_ids
        and relation.target_id in valid_ids
        and relation.relation_type in ontology.relation_types
    ]
    return ExtractionResult(entities=valid_entities, relations=valid_relations)


class LangChainExtractor:
    name = "langchain"

    def __init__(self) -> None:
        from langchain_openai import ChatOpenAI

        settings = get_settings()
        self.model = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.extraction_temperature,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            extra_body=(
                {"thinking": {"type": "disabled"}}
                if settings.llm_base_url and "deepseek.com" in settings.llm_base_url
                else None
            ),
        ).with_structured_output(
            ExtractionResult,
            method="function_calling",
            include_raw=True,
        )
        self.template = Template(Path(settings.prompt_path).read_text(encoding="utf-8"))

    def extract(self, sentence, context_before, context_after, ontology, run_index):
        prompt = self.template.render(
            sentence=sentence,
            context_before=context_before or "无",
            context_after=context_after or "无",
            run_index=run_index,
            entity_types=json.dumps(ontology.entity_types, ensure_ascii=False),
            relation_types=json.dumps(ontology.relation_types, ensure_ascii=False),
        )
        response = self.model.invoke(prompt)
        parsed = response.get("parsed")
        if parsed is None:
            raise ValueError("模型未返回可解析的结构化结果")
        return validate_result(parsed, sentence, ontology)


class RuleBasedExtractor:
    """Offline demo extractor. Domain dictionaries can be extended in ontology later."""

    name = "rule-demo"
    dictionaries = {
        "Material": ["氧化铝", "聚乙烯", "PE", "alumina", "polyethylene", "钢", "石墨烯"],
        "Property": ["断裂韧性", "硬度", "强度", "韧性", "导电性", "hardness", "toughness", "strength"],
        "Process": ["烧结", "退火", "制备", "合成", "sintering", "annealing"],
    }
    condition_pattern = re.compile(r"(?:-?\d+(?:\.\d+)?\s*(?:°C|℃|C|K|MPa|GPa|小时|h))|高温|低温|高压")

    def extract(self, sentence, context_before, context_after, ontology, run_index):
        entities: list[PredictedEntity] = []
        seen: set[tuple[int, int, str]] = set()
        for entity_type, terms in self.dictionaries.items():
            if entity_type not in ontology.entity_types:
                continue
            for term in terms:
                for match in re.finditer(re.escape(term), sentence, re.IGNORECASE):
                    key = (match.start(), match.end(), entity_type)
                    if key in seen:
                        continue
                    seen.add(key)
                    entities.append(PredictedEntity(
                        local_id=f"e{len(entities) + 1}", text=match.group(), entity_type=entity_type,
                        start=match.start(), end=match.end(),
                    ))
        if "Condition" in ontology.entity_types:
            for match in self.condition_pattern.finditer(sentence):
                entities.append(PredictedEntity(
                    local_id=f"e{len(entities) + 1}", text=match.group(), entity_type="Condition",
                    start=match.start(), end=match.end(),
                ))

        relations: list[PredictedRelation] = []
        materials = [e for e in entities if e.entity_type == "Material"]
        properties = [e for e in entities if e.entity_type == "Property"]
        conditions = [e for e in entities if e.entity_type == "Condition"]
        processes = [e for e in entities if e.entity_type == "Process"]
        if "HAS_PROPERTY" in ontology.relation_types:
            for material in materials:
                for prop in properties:
                    relations.append(PredictedRelation(
                        source_id=material.local_id, target_id=prop.local_id,
                        relation_type="HAS_PROPERTY", evidence=sentence,
                    ))
        if "UNDER_CONDITION" in ontology.relation_types:
            for owner in properties + processes:
                for condition in conditions:
                    relations.append(PredictedRelation(
                        source_id=owner.local_id, target_id=condition.local_id,
                        relation_type="UNDER_CONDITION", evidence=sentence,
                    ))
        return ExtractionResult(entities=entities, relations=relations)


def get_extractor() -> TripleExtractor:
    settings = get_settings()
    if settings.llm_api_key:
        return LangChainExtractor()
    return RuleBasedExtractor()
