from dataclasses import dataclass
from pathlib import Path

import yaml

from ..config import get_settings


@dataclass(frozen=True)
class Ontology:
    version: str
    entity_types: dict
    relation_types: dict


def load_ontology(path: Path | None = None) -> Ontology:
    target = path or get_settings().ontology_path
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    return Ontology(
        version=str(data["version"]),
        entity_types=data.get("entity_types", {}),
        relation_types=data.get("relation_types", {}),
    )
