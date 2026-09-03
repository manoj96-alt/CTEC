"""Repository for OQI-H4 governed relationship-cardinality persistence and
deterministic resolution (CDD-050 §7; Artifact Authorization row 8).

`acquire_cardinality_authority` follows the exact mechanism every other OQI
advisory lock uses. Seed `8` is the next available value in the OQI
advisory-lock seed registry (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6, 5=H1 coverage,
6=Reference Evidence, 7=CanonicalStandard) -- distinct from every existing
seed.

`get_active_cardinality_for_requirement` is the single query both Structural
Integrity evaluators consult -- resolution is anchored exclusively to
`relationship_requirement_id`, never inferred from `Obligation` alone
(CDD-050 §9)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_integrity.requirement import (
    IntegrityRelationshipCardinality,
    IntegrityRelationshipCardinalityStatus,
)
from app.infrastructure.persistence.models.oqi_integrity import (
    IntegrityRelationshipCardinalityORM,
)

#: CDD-050 §7: next available value in the OQI advisory-lock seed registry
#: (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6, 5=OQI-H1 coverage, 6=Reference Evidence,
#: 7=CanonicalStandard).
OQI_INTEGRITY_CARDINALITY_ADVISORY_LOCK_SEED = 8


class OqiIntegrityRequirementRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_cardinality_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_INTEGRITY_CARDINALITY_ADVISORY_LOCK_SEED},
        )

    def insert_cardinality(self, cardinality: IntegrityRelationshipCardinality) -> None:
        """A plain insert -- cardinality versions are immutable, never
        upserted. The database's partial unique index enforces "at most one
        ACTIVE version per RelationshipRequirement"; this method does not
        pre-check, so a violation surfaces as a real `IntegrityError`."""
        self.session.add(
            IntegrityRelationshipCardinalityORM(
                integrity_relationship_cardinality_id=(
                    cardinality.integrity_relationship_cardinality_id
                ),
                relationship_requirement_id=cardinality.relationship_requirement_id,
                min_cardinality=cardinality.min_cardinality,
                max_cardinality=cardinality.max_cardinality,
                version_number=cardinality.version_number,
                previous_version_id=cardinality.previous_version_id,
                status=cardinality.status.value,
                created_by=cardinality.created_by,
                created_on=cardinality.created_on,
                retired_on=cardinality.retired_on,
            )
        )
        self.session.flush()

    def retire_cardinality(
        self, *, integrity_relationship_cardinality_id: UUID, retired_on: datetime
    ) -> None:
        model = self.session.get(
            IntegrityRelationshipCardinalityORM, integrity_relationship_cardinality_id
        )
        if model is None:
            raise ValueError(
                f"no IntegrityRelationshipCardinality {integrity_relationship_cardinality_id}"
            )
        model.status = IntegrityRelationshipCardinalityStatus.RETIRED.value
        model.retired_on = retired_on

    def get_active_cardinality_for_requirement(
        self, *, relationship_requirement_id: UUID
    ) -> IntegrityRelationshipCardinality | None:
        model = self.session.execute(
            select(IntegrityRelationshipCardinalityORM).where(
                IntegrityRelationshipCardinalityORM.relationship_requirement_id
                == relationship_requirement_id,
                IntegrityRelationshipCardinalityORM.status
                == IntegrityRelationshipCardinalityStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        return None if model is None else self._to_domain(model)

    def get_cardinality_by_id(
        self, integrity_relationship_cardinality_id: UUID
    ) -> IntegrityRelationshipCardinality | None:
        model = self.session.get(
            IntegrityRelationshipCardinalityORM, integrity_relationship_cardinality_id
        )
        return None if model is None else self._to_domain(model)

    @staticmethod
    def _to_domain(
        model: IntegrityRelationshipCardinalityORM,
    ) -> IntegrityRelationshipCardinality:
        return IntegrityRelationshipCardinality(
            integrity_relationship_cardinality_id=model.integrity_relationship_cardinality_id,
            relationship_requirement_id=model.relationship_requirement_id,
            min_cardinality=model.min_cardinality,
            max_cardinality=model.max_cardinality,
            version_number=model.version_number,
            previous_version_id=model.previous_version_id,
            status=IntegrityRelationshipCardinalityStatus(model.status),
            created_by=model.created_by,
            created_on=model.created_on,
            retired_on=model.retired_on,
        )
