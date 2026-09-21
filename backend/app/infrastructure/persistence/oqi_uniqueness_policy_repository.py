"""Repository for OQI-H6 governed EnterpriseEntity Uniqueness policy
persistence (CDD-084 §15; Artifact Authorization row 7).

`acquire_policy_authority` follows the exact mechanism every other OQI
advisory lock uses. Seed `13` is the next available value in the OQI
advisory-lock seed registry (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6, 5=H1 coverage,
6=Reference Evidence, 7=CanonicalStandard, 8=IntegrityRelationshipCardinality,
9=Integrity Structural, 10=Integrity Reference, 11=Timeliness policy,
12=Timeliness evaluation) -- distinct from every existing seed.

`get_active_policy_for_entity_type` is the single query the Uniqueness
evaluator consults -- resolution is anchored exclusively to the exact
`(tenant_id, entity_type_id)` tuple (CDD-084 §15), never inferred."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_uniqueness.policy import UniquenessPolicy, UniquenessPolicyStatus
from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessPolicyORM

#: CDD-084 §15: next available value in the OQI advisory-lock seed registry
#: (1-12 already assigned across OQI1-6/H1-H5).
OQI_UNIQUENESS_POLICY_ADVISORY_LOCK_SEED = 13


class OqiUniquenessPolicyRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_policy_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_UNIQUENESS_POLICY_ADVISORY_LOCK_SEED},
        )

    def insert_policy(self, policy: UniquenessPolicy) -> None:
        """A plain insert -- policy versions are immutable, never upserted.
        The database's partial unique index enforces "at most one ACTIVE
        version per exact anchor tuple"; this method does not pre-check, so
        a violation surfaces as a real `IntegrityError`."""
        self.session.add(
            UniquenessPolicyORM(
                policy_id=policy.policy_id,
                version=policy.version,
                tenant_id=policy.tenant_id,
                entity_type_id=policy.entity_type_id,
                bucket_max_size=policy.bucket_max_size,
                status=policy.status.value,
                created_by=policy.created_by,
                created_on=policy.created_on,
            )
        )
        self.session.flush()

    def retire_policy(self, *, tenant_id: str, policy_id: UUID, version: int) -> None:
        model = self.session.get(UniquenessPolicyORM, (policy_id, version))
        if model is None or model.tenant_id != tenant_id:
            raise ValueError(f"no UniquenessPolicy {policy_id} v{version} for tenant {tenant_id!r}")
        model.status = UniquenessPolicyStatus.RETIRED.value

    def get_active_policy_for_entity_type(
        self, *, tenant_id: str, entity_type_id: UUID
    ) -> UniquenessPolicy | None:
        model = self.session.execute(
            select(UniquenessPolicyORM).where(
                UniquenessPolicyORM.tenant_id == tenant_id,
                UniquenessPolicyORM.entity_type_id == entity_type_id,
                UniquenessPolicyORM.status == UniquenessPolicyStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        return None if model is None else self._to_domain(model)

    def get_policy_by_id(self, *, policy_id: UUID, version: int) -> UniquenessPolicy | None:
        model = self.session.get(UniquenessPolicyORM, (policy_id, version))
        return None if model is None else self._to_domain(model)

    @staticmethod
    def _to_domain(model: UniquenessPolicyORM) -> UniquenessPolicy:
        return UniquenessPolicy(
            policy_id=model.policy_id,
            version=model.version,
            tenant_id=model.tenant_id,
            entity_type_id=model.entity_type_id,
            bucket_max_size=model.bucket_max_size,
            status=UniquenessPolicyStatus(model.status),
            created_by=model.created_by,
            created_on=model.created_on,
        )
