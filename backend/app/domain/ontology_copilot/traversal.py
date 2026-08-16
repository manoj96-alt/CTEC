"""Deterministic, read-only ontology traversal for Ask CTEC (Gate D). Pure
domain logic: operates only on already-persisted, already-tenant-scoped data
handed to it by the application/persistence layer (see
app.infrastructure.persistence.institutional_relationship_store). Never
queries a database itself, never invokes any Cognitive Engine capability
(ERM/SRM/ASM/KRM/DRM/GRM), and never invents an edge or entity not present in
the supplied data -- exactly the boundary the PAD-001 Product-Internal
Deterministic Capability Boundary Clarification (architecture/released/v1.9/)
requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

MAX_TRAVERSAL_DEPTH = 6


@dataclass(frozen=True, slots=True)
class GraphEntity:
    entity_id: UUID
    entity_name: str
    entity_type_name: str


@dataclass(frozen=True, slots=True)
class GraphEdge:
    relationship_name: str
    from_entity_id: UUID
    to_entity_id: UUID


@dataclass(frozen=True, slots=True)
class EvidenceStep:
    step: int
    entity_id: UUID
    entity_name: str
    entity_type_name: str
    # The relationship that leaves this step toward the next one in the same
    # path; None on a path's final step, since nothing leaves it.
    relationship_name: str | None


@dataclass(frozen=True, slots=True)
class TraversalPath:
    target_entity_id: UUID
    target_entity_name: str
    steps: tuple[EvidenceStep, ...]


def find_paths_to_target_type(
    *,
    start_entity: GraphEntity,
    entities_by_id: dict[UUID, GraphEntity],
    edges: tuple[GraphEdge, ...],
    target_entity_type_name: str,
    max_depth: int = MAX_TRAVERSAL_DEPTH,
) -> tuple[TraversalPath, ...]:
    """Deterministic breadth-first search from start_entity, following only
    the supplied persisted edges, returning every distinct simple path
    (never revisiting an entity within the same path) that reaches an entity
    whose entity_type_name equals target_entity_type_name. A path stops the
    moment it reaches a matching entity -- it is not traversed further past
    that point. Bounded by max_depth so traversal stays finite and
    deterministic even against unexpectedly cyclic persisted data. Results
    are sorted by target entity name, then id, for stable, repeatable
    ordering.
    """
    adjacency: dict[UUID, list[GraphEdge]] = {}
    for edge in edges:
        adjacency.setdefault(edge.from_entity_id, []).append(edge)
    for neighbors in adjacency.values():
        neighbors.sort(key=lambda e: (e.relationship_name, str(e.to_entity_id)))

    initial_step = EvidenceStep(
        step=1,
        entity_id=start_entity.entity_id,
        entity_name=start_entity.entity_name,
        entity_type_name=start_entity.entity_type_name,
        relationship_name=None,
    )
    queue: list[tuple[UUID, tuple[EvidenceStep, ...], frozenset[UUID]]] = [
        (start_entity.entity_id, (initial_step,), frozenset({start_entity.entity_id}))
    ]
    results: list[TraversalPath] = []

    while queue:
        current_id, path_so_far, visited = queue.pop(0)
        if len(path_so_far) > max_depth + 1:
            continue
        current_entity = entities_by_id.get(current_id)
        if current_entity is None:
            continue
        if len(path_so_far) > 1 and current_entity.entity_type_name == target_entity_type_name:
            results.append(
                TraversalPath(
                    target_entity_id=current_id,
                    target_entity_name=current_entity.entity_name,
                    steps=path_so_far,
                )
            )
            continue

        for edge in adjacency.get(current_id, ()):
            if edge.to_entity_id in visited:
                continue
            next_entity = entities_by_id.get(edge.to_entity_id)
            if next_entity is None:
                continue
            updated_last = EvidenceStep(
                step=path_so_far[-1].step,
                entity_id=path_so_far[-1].entity_id,
                entity_name=path_so_far[-1].entity_name,
                entity_type_name=path_so_far[-1].entity_type_name,
                relationship_name=edge.relationship_name,
            )
            new_step = EvidenceStep(
                step=len(path_so_far) + 1,
                entity_id=next_entity.entity_id,
                entity_name=next_entity.entity_name,
                entity_type_name=next_entity.entity_type_name,
                relationship_name=None,
            )
            new_path = path_so_far[:-1] + (updated_last, new_step)
            queue.append((edge.to_entity_id, new_path, visited | {edge.to_entity_id}))

    results.sort(key=lambda p: (p.target_entity_name, str(p.target_entity_id)))
    return tuple(results)
