"""Internal Gate L -- AI-Assisted Semantic Mapping Candidate Discovery
(CDD-027 §11.1, §14, §16, §17; AI-Assisted Semantic Mapping Candidate
Discovery Artifact Authorization §4.1). Deterministically constructs the
tenant-bounded `SourceField` candidate universe and its bounded semantic
metadata projection for one already-identified `InformationElementRequirement`
gap, and defines the sole provider-neutral candidate-discovery port. The
candidate universe is read-only: this module performs no mutation of any
kind. `SemanticMappingCandidateProvider` may only select a `source_field_id`
already present in the supplied universe, or abstain -- it can never expand
the universe, never receive raw `FieldValueEvidence`, never establish
tenant, and never redefine the target `InformationElementRequirement`, which
is supplied by the caller and never echoed back by the provider."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.blueprint import Obligation
from app.domain.shared.enums import GovernanceStatus
from app.infrastructure.persistence.models.semantic_mapping import SemanticMappingORM
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM


@dataclass(frozen=True, slots=True)
class CandidateSourceField:
    source_field_id: UUID
    field_label: str
    source_object_id: UUID
    source_object_name: str
    source_system_id: UUID
    source_system_name: str


@dataclass(frozen=True, slots=True)
class CandidateDiscoveryContext:
    information_element_requirement_id: UUID
    element_name: str
    description: str
    obligation: Obligation
    candidate_source_fields: tuple[CandidateSourceField, ...]


@dataclass(frozen=True, slots=True)
class CandidateSelection:
    source_field_id: UUID


class SemanticMappingCandidateProvider(Protocol):
    def discover(self, *, context: CandidateDiscoveryContext) -> CandidateSelection | None: ...


class SemanticMappingCandidateUniverseService:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    def build_context(
        self,
        *,
        tenant_id: str,
        information_element_requirement_id: UUID,
        element_name: str,
        description: str,
        obligation: Obligation,
    ) -> CandidateDiscoveryContext:
        approved_source_field_ids = set(
            self._session.scalars(
                select(SemanticMappingORM.source_field_id).where(
                    SemanticMappingORM.governance_status == GovernanceStatus.APPROVED.value
                )
            ).all()
        )

        rows = self._session.execute(
            select(SourceFieldORM, SourceObjectORM, SourceSystemORM)
            .join(
                SourceObjectORM,
                SourceObjectORM.source_object_id == SourceFieldORM.source_object_id,
            )
            .join(
                SourceSystemORM,
                SourceSystemORM.source_system_id == SourceObjectORM.source_system_id,
            )
            .where(SourceObjectORM.tenant_id == tenant_id)
            .order_by(SourceFieldORM.source_field_id)
        ).all()

        candidates = tuple(
            CandidateSourceField(
                source_field_id=source_field.source_field_id,
                field_label=source_field.field_label,
                source_object_id=source_object.source_object_id,
                source_object_name=source_object.source_object_name,
                source_system_id=source_system.source_system_id,
                source_system_name=source_system.source_system_name,
            )
            for source_field, source_object, source_system in rows
            if source_field.source_field_id not in approved_source_field_ids
        )

        return CandidateDiscoveryContext(
            information_element_requirement_id=information_element_requirement_id,
            element_name=element_name,
            description=description,
            obligation=obligation,
            candidate_source_fields=candidates,
        )
