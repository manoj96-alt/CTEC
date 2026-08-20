"""Internal Semantic Mapping Resolution application service (Gate H H2;
CDD-019 §14; H2 Semantic Mapping Resolution Artifact Authorization).
Provides the governed internal application/use-case read boundary CDD-019
§14 describes: for a given tenant and `information_element_requirement_id`,
what is the Approved `SourceField` (if any) the governed `SemanticMapping`
resolves to? Performs no persistence of its own: delegates entirely to the
unmodified H1 `SemanticMappingRepository`, matching
`BlueprintApplicationService`'s constructor-injection, one-line-delegation
pattern."""

from uuid import UUID

from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepository,
    SemanticMappingResolution,
)


class SemanticMappingResolutionApplicationService:
    def __init__(self, *, repository: SemanticMappingRepository) -> None:
        self.repository = repository

    def resolve_approved_source_field(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> SemanticMappingResolution | None:
        return self.repository.get_approved_by_information_element_requirement(
            information_element_requirement_id, tenant_id
        )
