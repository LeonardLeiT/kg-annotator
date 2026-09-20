from __future__ import annotations

from app.models import Sentence
from app.schemas import SentenceSuggestion

from .extraction import TripleExtractor, get_llm_extractor
from .ontology import Ontology, load_ontology


def suggest_sentence(
    sentence: Sentence,
    *,
    extractor: TripleExtractor | None = None,
    ontology: Ontology | None = None,
) -> SentenceSuggestion:
    """Generate a transient suggestion for one sentence without writing to the DB."""
    active_extractor = extractor or get_llm_extractor()
    active_ontology = ontology or load_ontology()
    result = active_extractor.extract(
        sentence.text,
        sentence.context_before,
        sentence.context_after,
        active_ontology,
        run_index=1,
    )
    return SentenceSuggestion(
        model=active_extractor.name,
        entities=result.entities,
        relations=result.relations,
    )
