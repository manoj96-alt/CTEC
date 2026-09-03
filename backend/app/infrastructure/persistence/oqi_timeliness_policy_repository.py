"""Repository for OQI-H5 governed Timeliness policy persistence (CDD-051
§8; Artifact Authorization row 6).

`acquire_policy_authority` follows the exact mechanism every other OQI
advisory lock uses. Seed `11` is the next available value in the OQI
advisory-lock seed registry (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6, 5=H1 coverage,
6=Reference Evidence, 7=CanonicalStandard, 8=IntegrityRelationshipCardinality,
9=Integrity Structural, 10=Integrity Reference) -- distinct from every
existing seed.

`get_active_policy_for_anchor` is the single query the Timeliness evaluator
consults -- resolution is anchored exclusively to the exact
`(information_element_requirement_id, business_process_id,
business_process_version)` tuple (CDD-051 §7-§8), never inferred."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_timeliness.policy import TimelinessPolicy, TimelinessPolicyStatus
from app.infrastructure.persistence.models.oqi_timeliness import TimelinessPolicyORM

#: CDD-051 §8: next available value in the OQI advisory-lock seed registry
#: (1-10 already assigned across OQI1-6/H1-H4).
OQI_TIMELINESS_POLICY_ADVISORY_LOCK_SEED = 11


class OqiTimelinessPolicyRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_policy_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_TIMELINESS_POLICY_ADVISORY_LOCK_SEED},
        )

    def insert_policy(self, policy: TimelinessPolicy) -> None:
        """A plain insert -- policy versions are immutable, never upserted.
        The database's partial unique index enforces "at most one ACTIVE
        version per exact anchor tuple"; this method does not pre-check, so
        a violation surfaces as a real `IntegrityError`."""
        self.session.add(
            TimelinessPolicyORM(
                policy_id=policy.policy_id,
                version=policy.version,
                tenant_id=policy.tenant_id,
                information_element_requirement_id=policy.information_element_requirement_id,
                business_process_id=policy.business_process_id,
                business_process_version=policy.business_process_version,
                freshness_window_seconds=policy.freshness_window_seconds,
                ingestion_sla_seconds=policy.ingestion_sla_seconds,
                status=policy.status.value,
                created_by=policy.created_by,
                created_on=policy.created_on,
            )
        )
        self.session.flush()

    def retire_policy(self, *, tenant_id: str, policy_id: UUID, version: int) -> None:
        model = self.session.get(TimelinessPolicyORM, (policy_id, version))
        if model is None or model.tenant_id != tenant_id:
            raise ValueError(f"no TimelinessPolicy {policy_id} v{version} for tenant {tenant_id!r}")
        model.status = TimelinessPolicyStatus.RETIRED.value

    def get_active_policy_for_anchor(
        self,
        *,
        tenant_id: str,
        information_element_requirement_id: UUID,
        business_process_id: UUID,
        business_process_version: int,
    ) -> TimelinessPolicy | None:
        model = self.session.execute(
            select(TimelinessPolicyORM).where(
                TimelinessPolicyORM.tenant_id == tenant_id,
                TimelinessPolicyORM.information_element_requirement_id
                == information_element_requirement_id,
                TimelinessPolicyORM.business_process_id == business_process_id,
                TimelinessPolicyORM.business_process_version == business_process_version,
                TimelinessPolicyORM.status == TimelinessPolicyStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        return None if model is None else self._to_domain(model)

    def get_policy_by_id(self, *, policy_id: UUID, version: int) -> TimelinessPolicy | None:
        model = self.session.get(TimelinessPolicyORM, (policy_id, version))
        return None if model is None else self._to_domain(model)

    @staticmethod
    def _to_domain(model: TimelinessPolicyORM) -> TimelinessPolicy:
        return TimelinessPolicy(
            policy_id=model.policy_id,
            version=model.version,
            tenant_id=model.tenant_id,
            information_element_requirement_id=model.information_element_requirement_id,
            business_process_id=model.business_process_id,
            business_process_version=model.business_process_version,
            freshness_window_seconds=model.freshness_window_seconds,
            ingestion_sla_seconds=model.ingestion_sla_seconds,
            status=TimelinessPolicyStatus(model.status),
            created_by=model.created_by,
            created_on=model.created_on,
        )
