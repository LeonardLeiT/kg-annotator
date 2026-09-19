from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas import ExtractionResult, PredictedEntity


def overlap_ratio(a: PredictedEntity, b: PredictedEntity) -> float:
    overlap = max(0, min(a.end, b.end) - max(a.start, b.start))
    union = max(a.end, b.end) - min(a.start, b.start)
    return overlap / union if union else 0.0


def entities_match(a: PredictedEntity, b: PredictedEntity) -> bool:
    if a.entity_type != b.entity_type:
        return False
    return (a.start == b.start and a.end == b.end) or overlap_ratio(a, b) >= 0.5


@dataclass
class EntityGroup:
    members: list[tuple[int, PredictedEntity]] = field(default_factory=list)

    @property
    def preferred(self) -> PredictedEntity:
        counts: dict[tuple[int, int, str, str], int] = {}
        for _, item in self.members:
            key = (item.start, item.end, item.text, item.entity_type)
            counts[key] = counts.get(key, 0) + 1
        best = max(counts, key=lambda key: (counts[key], key[1] - key[0]))
        return next(item for _, item in self.members if (item.start, item.end, item.text, item.entity_type) == best)

    @property
    def votes(self) -> int:
        return len({run_index for run_index, _ in self.members})


@dataclass
class RelationGroup:
    source_group: int
    relation_type: str
    target_group: int
    runs: set[int] = field(default_factory=set)


def aggregate_results(results: list[ExtractionResult]) -> tuple[list[EntityGroup], list[RelationGroup]]:
    groups: list[EntityGroup] = []
    local_to_group: dict[tuple[int, str], int] = {}

    for run_index, result in enumerate(results, start=1):
        for entity in result.entities:
            group_index = next(
                (index for index, group in enumerate(groups) if entities_match(group.preferred, entity)),
                None,
            )
            if group_index is None:
                groups.append(EntityGroup())
                group_index = len(groups) - 1
            groups[group_index].members.append((run_index, entity))
            local_to_group[(run_index, entity.local_id)] = group_index

    relation_map: dict[tuple[int, str, int], RelationGroup] = {}
    for run_index, result in enumerate(results, start=1):
        for relation in result.relations:
            source = local_to_group.get((run_index, relation.source_id))
            target = local_to_group.get((run_index, relation.target_id))
            if source is None or target is None:
                continue
            key = (source, relation.relation_type, target)
            relation_map.setdefault(key, RelationGroup(source, relation.relation_type, target)).runs.add(run_index)

    return groups, list(relation_map.values())
