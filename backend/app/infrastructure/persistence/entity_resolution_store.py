import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.identity_resolution import EnterpriseEntityResolutionRecord
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionHistoryModel,
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.source_object import SourceObject


class CrossTenantReferenceError(Exception):
    """Raised when a record would reference data owned by another tenant.

    supporting_source_object_ids is a pre-existing JSON array (see 0002),
    not a relational column, so PostgreSQL cannot enforce this particular
    reference with a foreign key. This is the application-boundary
    enforcement for that specific gap; every other tenant-owned reference
    introduced by this increment (enterprise_entity_id, policy_id, the
    history-to-record link) is additionally enforced by a real composite
    foreign key and will raise sqlalchemy.exc.IntegrityError instead.
    """


class EntityResolutionStore:
    """Append immutable records and maintain currentness outside record state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def understanding_key(source_ids: tuple[UUID, ...]) -> str:
        canonical = ",".join(sorted(str(value) for value in source_ids))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _assert_source_objects_owned_by_tenant(
        self, record: EnterpriseEntityResolutionRecord
    ) -> None:
        owned_ids = set(
            self.session.scalars(
                select(SourceObject.source_object_id).where(
                    SourceObject.source_object_id.in_(record.supporting_source_object_ids),
                    SourceObject.tenant_id == record.tenant_id,
                )
            )
        )
        missing = set(record.supporting_source_object_ids) - owned_ids
        if missing:
            raise CrossTenantReferenceError(
                "supporting_source_object_ids reference source objects not owned by "
                f"tenant {record.tenant_id!r}: {sorted(str(v) for v in missing)}"
            )

    def append(self, record: EnterpriseEntityResolutionRecord) -> None:
        self._assert_source_objects_owned_by_tenant(record)
        model = EnterpriseEntityResolutionRecordModel(
            record_id=record.record_id,
            tenant_id=record.tenant_id,
            enterprise_entity_id=record.enterprise_entity_id,
            supporting_source_object_ids=[
                str(value) for value in record.supporting_source_object_ids
            ],
            outcome=record.outcome.value,
            business_confidence=record.business_confidence.value,
            structured_reasons=list(record.structured_reasons),
            narrative_explanation=record.narrative_explanation,
            produced_at=record.produced_at,
            policy_version=record.policy_version,
            evidence_profile=(
                record.evidence_profile.as_record() if record.evidence_profile is not None else None
            ),
            policy_id=record.policy_id,
            actor_id=record.actor_id,
            decision_rationale=record.decision_rationale,
        )
        self.session.add(model)
        key = self.understanding_key(record.supporting_source_object_ids)
        record_history = self.session.get(EnterpriseEntityResolutionHistoryModel, key)
        if record_history is None:
            self.session.add(
                EnterpriseEntityResolutionHistoryModel(
                    understanding_key=key,
                    tenant_id=record.tenant_id,
                    current_record_identifier=record.record_id,
                    historical_record_references=[],
                    updated_at=record.produced_at,
                )
            )
        else:
            if record_history.tenant_id != record.tenant_id:
                raise CrossTenantReferenceError(
                    f"Understanding key {key!r} is already owned by tenant "
                    f"{record_history.tenant_id!r}, not {record.tenant_id!r}"
                )
            record_history.historical_record_references = [
                *record_history.historical_record_references,
                str(record_history.current_record_identifier),
            ]
            record_history.current_record_identifier = record.record_id
            record_history.updated_at = record.produced_at

    def list_current_records(self, tenant_id: str) -> list[EnterpriseEntityResolutionRecordModel]:
        """Tenant-scoped read of the current record for every case. Filters
        both the history projection and the record itself by tenant_id, so a
        cross-tenant collision at either layer cannot surface a result."""
        current_ids = self.session.scalars(
            select(EnterpriseEntityResolutionHistoryModel.current_record_identifier).where(
                EnterpriseEntityResolutionHistoryModel.tenant_id == tenant_id
            )
        ).all()
        if not current_ids:
            return []
        return list(
            self.session.scalars(
                select(EnterpriseEntityResolutionRecordModel).where(
                    EnterpriseEntityResolutionRecordModel.tenant_id == tenant_id,
                    EnterpriseEntityResolutionRecordModel.record_id.in_(current_ids),
                )
            ).all()
        )

    def get_current_record(
        self, tenant_id: str, understanding_key: str
    ) -> EnterpriseEntityResolutionRecordModel | None:
        """Tenant-scoped case lookup. Returns None (never another tenant's
        row) for an unknown, foreign-tenant, or tampered-with key."""
        history = self.session.get(EnterpriseEntityResolutionHistoryModel, understanding_key)
        if history is None or history.tenant_id != tenant_id:
            return None
        record = self.session.get(
            EnterpriseEntityResolutionRecordModel, history.current_record_identifier
        )
        if record is None or record.tenant_id != tenant_id:
            return None
        return record
