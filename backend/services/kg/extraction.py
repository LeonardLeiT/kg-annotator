from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from jinja2 import Template
from app.config import get_settings
from app.schemas import ExtractionResult, PredictedEntity
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
        self.name = settings.llm_model
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


class LLMNotConfiguredError(RuntimeError):
    pass


def get_llm_extractor() -> TripleExtractor:
    """Return the configured LLM extractor without an offline fallback."""
    if not get_settings().llm_api_key:
        raise LLMNotConfiguredError("未配置 LLM API 密钥")
    return LangChainExtractor()
