"""Repository for OQI-H4 Structural Integrity evaluation persistence
(CDD-050 §10.1, §12; Artifact Authorization row 9).

`select_qualifying_relationships` is the exact frozen qualifying-relationship
query (CDD-050 §10.1): same tenant, `from_entity_id` = the evaluated entity,
exact `relationship_type_id`, target `EnterpriseEntity.entity_type_id` =
`RelationshipRequirement.target_entity_type_id`, `governance_status =
'Approved'`, `lifecycle_state = 'Active'`, `superseded_by_id IS NULL`. Never
performs Entity Resolution, never infers a target, never accepts
cross-tenant graph state -- a pure, deterministic read against
`InstitutionalRelationship`/`EnterpriseEntity`.

`acquire_evaluation_authority` reuses a dedicated seed (9), distinct from the
cardinality-policy repository's own seed (8) and every other existing OQI
seed."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_integrity.structural import (
    IntegrityFindingStatus,
    IntegrityFindingType,
    StructuralIntegrityFinding,
)
from app.infrastructure.persistence.models.blueprint import RelationshipRequirementORM
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.oqi_integrity import (
    IntegrityStructuralEvaluationORM,
    IntegrityStructuralEvaluationRelationshipORM,
    IntegrityStructuralFindingORM,
)

#: CDD-050 §7: distinct from OqiIntegrityRequirementRepositoryImpl's own
#: seed (8) and every existing OQI seed (1-7).
OQI_INTEGRITY_STRUCTURAL_ADVISORY_LOCK_SEED = 9


class OqiIntegrityStructuralEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_INTEGRITY_STRUCTURAL_ADVISORY_LOCK_SEED},
        )

    def get_relationship_requirement_info(
        self, relationship_requirement_id: UUID
    ) -> tuple[UUID, UUID, str] | None:
        """Returns `(relationship_type_id, target_entity_type_id,
        obligation)` for the governed `RelationshipRequirement` -- read-only,
        never modified (CDD-017, unmodified by CDD-050)."""
        row = self.session.execute(
            select(
                RelationshipRequirementORM.relationship_type_id,
                RelationshipRequirementORM.target_entity_type_id,
                RelationshipRequirementORM.obligation,
            ).where(
                RelationshipRequirementORM.relationship_requirement_id
                == relationship_requirement_id
            )
        ).first()
        return None if row is None else (row[0], row[1], row[2])

    def select_qualifying_relationships(
        self,
        *,
        tenant_id: str,
        enterprise_entity_id: UUID,
        relationship_type_id: UUID,
        target_entity_type_id: UUID,
    ) -> tuple[tuple[UUID, UUID], ...]:
        """CDD-050 §10.1's exact qualifying-relationship filter. Returns
        `(institutional_relationship_id, target_enterprise_entity_id)` pairs
        -- one row per qualifying edge, never deduplicated here (distinct-
        target counting, PO-H4-01, is the caller's own responsibility, since
        the raw pairs are also this evaluation's own provenance, CDD-050
        §17)."""
        rows = self.session.execute(
            select(
                InstitutionalRelationship.institutional_relationship_id,
                InstitutionalRelationship.to_entity_id,
            )
            .join(
                EnterpriseEntity,
                EnterpriseEntity.enterprise_entity_id == InstitutionalRelationship.to_entity_id,
            )
            .where(
                InstitutionalRelationship.tenant_id == tenant_id,
                InstitutionalRelationship.from_entity_id == enterprise_entity_id,
                InstitutionalRelationship.relationship_type_id == relationship_type_id,
                EnterpriseEntity.tenant_id == tenant_id,
                EnterpriseEntity.entity_type_id == target_entity_type_id,
                InstitutionalRelationship.governance_status == "Approved",
                InstitutionalRelationship.lifecycle_state == "Active",
                InstitutionalRelationship.superseded_by_id.is_(None),
            )
        ).all()
        return tuple((row[0], row[1]) for row in rows)

    def get_finding(self, finding_id: UUID) -> StructuralIntegrityFinding | None:
        model = self.session.get(IntegrityStructuralFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def insert_evaluation_idempotent(
        self,
        *,
        evaluation_id: UUID,
        tenant_id: str,
        relationship_requirement_id: UUID,
        integrity_relationship_cardinality_id: UUID,
        enterprise_entity_id: UUID,
        qualifying_relationships: tuple[tuple[UUID, UUID], ...],
        qualifying_target_count: int,
        outcome: str,
        evaluation_horizon: datetime,
        evaluated_on: datetime,
    ) -> bool:
        existing = self.session.get(IntegrityStructuralEvaluationORM, evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            IntegrityStructuralEvaluationORM(
                evaluation_id=evaluation_id,
                tenant_id=tenant_id,
                relationship_requirement_id=relationship_requirement_id,
                integrity_relationship_cardinality_id=integrity_relationship_cardinality_id,
                enterprise_entity_id=enterprise_entity_id,
                qualifying_target_count=qualifying_target_count,
                outcome=outcome,
                evaluation_horizon=evaluation_horizon,
                evaluated_on=evaluated_on,
            )
        )
        self.session.flush()
        for institutional_relationship_id, _target_id in qualifying_relationships:
            self.session.add(
                IntegrityStructuralEvaluationRelationshipORM(
                    evaluation_id=evaluation_id,
                    institutional_relationship_id=institutional_relationship_id,
                )
            )
        self.session.flush()
        return True

    def upsert_finding(self, finding: StructuralIntegrityFinding) -> None:
        model = self.session.get(IntegrityStructuralFindingORM, finding.finding_id)
        if model is None:
            self.session.add(_finding_to_orm(finding))
            return
        model.finding_type = finding.finding_type.value
        model.status = finding.status.value
        model.state_revision = finding.state_revision
        model.last_seen_at = finding.last_seen_at
        model.last_evaluated_horizon = finding.last_evaluated_horizon
        model.occurrence_count = finding.occurrence_count
        model.reopen_count = finding.reopen_count

    def has_qualifying_coverage(
        self, *, tenant_id: str, enterprise_entity_ids: tuple[UUID, ...]
    ) -> bool:
        """CDD-050 §24 (H1 coverage): existence-only, subject-scoped -- at
        least one Structural Integrity evaluation row (any outcome) exists
        for one of the caller-supplied entities."""
        if not enterprise_entity_ids:
            return False
        return (
            self.session.execute(
                select(IntegrityStructuralEvaluationORM.evaluation_id)
                .where(
                    IntegrityStructuralEvaluationORM.tenant_id == tenant_id,
                    IntegrityStructuralEvaluationORM.enterprise_entity_id.in_(
                        enterprise_entity_ids
                    ),
                )
                .limit(1)
            ).first()
            is not None
        )


def _finding_to_orm(finding: StructuralIntegrityFinding) -> IntegrityStructuralFindingORM:
    return IntegrityStructuralFindingORM(
        finding_id=finding.finding_id,
        tenant_id=finding.tenant_id,
        relationship_requirement_id=finding.relationship_requirement_id,
        enterprise_entity_id=finding.enterprise_entity_id,
        finding_type=finding.finding_type.value,
        status=finding.status.value,
        state_revision=finding.state_revision,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        last_evaluated_horizon=finding.last_evaluated_horizon,
        occurrence_count=finding.occurrence_count,
        reopen_count=finding.reopen_count,
    )


def _finding_to_domain(model: IntegrityStructuralFindingORM) -> StructuralIntegrityFinding:
    return StructuralIntegrityFinding(
        finding_id=model.finding_id,
        tenant_id=model.tenant_id,
        relationship_requirement_id=model.relationship_requirement_id,
        enterprise_entity_id=model.enterprise_entity_id,
        finding_type=IntegrityFindingType(model.finding_type),
        status=IntegrityFindingStatus(model.status),
        state_revision=model.state_revision,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        last_evaluated_horizon=model.last_evaluated_horizon,
        occurrence_count=model.occurrence_count,
        reopen_count=model.reopen_count,
    )
