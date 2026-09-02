"""Repository for OQI-H2 governed Reference Evidence persistence and
qualifying-assertion lookup (CDD-048 §15-§16; Artifact Authorization row 4).

`acquire_reference_evidence_authority` follows the exact GR-selected
mechanism every other OQI advisory lock uses:
`SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))`. Seed `6`
is the next available value in the OQI advisory-lock seed registry
(1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6, 5=OQI-H1 coverage) -- distinct from every
existing seed so this subsystem's serialization domain can never
coincidentally collide with another's.

`find_active_assertions_for_subject` is the single query both the Accuracy
evaluator (selecting qualifying Reference Evidence) and conflict detection
(CDD-048 §16) consume -- "qualifying" means ACTIVE, regardless of form; an
inactive/superseded/RETIRED assertion never qualifies (CDD-048 §8, case
"Reference Evidence stale/inactive/superseded")."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_reference_evidence.assertion import (
    BusinessRuleDerivedReferenceEntry,
    GovernedReferenceDatasetEntry,
    HumanVerifiedEvidenceEntry,
    ReferenceEvidenceAssertion,
    ReferenceEvidenceForm,
    ReferenceEvidenceStatus,
)
from app.domain.oqi_reference_evidence.conflict import (
    OqiReferenceEvidenceConflict,
    ReferenceEvidenceConflictStatus,
)
from app.infrastructure.persistence.models.oqi_reference_evidence import (
    BusinessRuleDerivedReferenceEntryORM,
    GovernedReferenceDatasetEntryORM,
    HumanVerifiedEvidenceEntryORM,
    OqiReferenceEvidenceConflictMemberORM,
    OqiReferenceEvidenceConflictORM,
    ReferenceEvidenceAssertionORM,
)

#: CDD-048 §26: next available value in the OQI advisory-lock seed registry
#: (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6, 5=OQI-H1 coverage).
OQI_REFERENCE_EVIDENCE_ADVISORY_LOCK_SEED = 6


class OqiReferenceEvidenceRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Advisory lock (dedicated seed 6).
    # ------------------------------------------------------------------

    def acquire_reference_evidence_authority(self, identity: str) -> None:
        """Transaction-scoped: releases automatically on COMMIT, ROLLBACK,
        or connection loss. Serializes the read-latest-version-then-insert-
        next-version sequence for one logical (tenant, subject, form) against
        concurrent callers; the database's own partial ACTIVE-uniqueness
        index remains the actual safety guarantee regardless."""
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_REFERENCE_EVIDENCE_ADVISORY_LOCK_SEED},
        )

    # ------------------------------------------------------------------
    # Assertion persistence.
    # ------------------------------------------------------------------

    def insert_assertion(self, assertion: ReferenceEvidenceAssertion) -> None:
        """A plain insert -- assertion versions are immutable, never
        upserted. The database's partial unique index enforces "at most one
        ACTIVE version per (tenant, subject, form)"; this method does not
        pre-check, so a violation surfaces as a real `IntegrityError`."""
        self.session.add(
            ReferenceEvidenceAssertionORM(
                assertion_id=assertion.assertion_id,
                tenant_id=assertion.tenant_id,
                ontology_element_type=assertion.ontology_element_type.value,
                ontology_element_id=assertion.ontology_element_id,
                source_field_id=assertion.source_field_id,
                form=assertion.form.value,
                asserted_value=assertion.asserted_value,
                status=assertion.status.value,
                version_number=assertion.version_number,
                previous_version_id=assertion.previous_version_id,
                created_by=assertion.created_by,
                created_on=assertion.created_on,
                retired_on=assertion.retired_on,
            )
        )
        self.session.flush()

    def retire_assertion(self, *, assertion_id: UUID, retired_on: datetime) -> None:
        model = self.session.get(ReferenceEvidenceAssertionORM, assertion_id)
        if model is None:
            raise ValueError(f"no ReferenceEvidenceAssertion {assertion_id}")
        model.status = ReferenceEvidenceStatus.RETIRED.value
        model.retired_on = retired_on

    def insert_governed_reference_dataset_entry(self, entry: GovernedReferenceDatasetEntry) -> None:
        self.session.add(
            GovernedReferenceDatasetEntryORM(
                assertion_id=entry.assertion_id,
                dataset_name=entry.dataset_name,
                dataset_version=entry.dataset_version,
                entry_key=entry.entry_key,
            )
        )

    def insert_human_verified_evidence_entry(self, entry: HumanVerifiedEvidenceEntry) -> None:
        self.session.add(
            HumanVerifiedEvidenceEntryORM(
                assertion_id=entry.assertion_id,
                verifying_actor_id=entry.verifying_actor_id,
                verification_timestamp=entry.verification_timestamp,
                verification_rationale=entry.verification_rationale,
                revoked_at=entry.revoked_at,
            )
        )

    def insert_business_rule_derived_reference_entry(
        self, entry: BusinessRuleDerivedReferenceEntry
    ) -> None:
        self.session.add(
            BusinessRuleDerivedReferenceEntryORM(
                assertion_id=entry.assertion_id,
                deriving_business_rule_id=entry.deriving_business_rule_id,
                deriving_rule_version=entry.deriving_rule_version,
                deriving_evaluation_id=entry.deriving_evaluation_id,
            )
        )

    def get_active_assertion(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
        form: ReferenceEvidenceForm,
    ) -> ReferenceEvidenceAssertion | None:
        model = (
            self.session.query(ReferenceEvidenceAssertionORM)
            .filter(
                ReferenceEvidenceAssertionORM.tenant_id == tenant_id,
                ReferenceEvidenceAssertionORM.ontology_element_type == ontology_element_type.value,
                ReferenceEvidenceAssertionORM.ontology_element_id == ontology_element_id,
                ReferenceEvidenceAssertionORM.source_field_id == source_field_id,
                ReferenceEvidenceAssertionORM.form == form.value,
                ReferenceEvidenceAssertionORM.status == ReferenceEvidenceStatus.ACTIVE.value,
            )
            .one_or_none()
        )
        return None if model is None else _assertion_to_domain(model)

    def get_latest_assertion_version(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
        form: ReferenceEvidenceForm,
    ) -> ReferenceEvidenceAssertion | None:
        model = (
            self.session.query(ReferenceEvidenceAssertionORM)
            .filter(
                ReferenceEvidenceAssertionORM.tenant_id == tenant_id,
                ReferenceEvidenceAssertionORM.ontology_element_type == ontology_element_type.value,
                ReferenceEvidenceAssertionORM.ontology_element_id == ontology_element_id,
                ReferenceEvidenceAssertionORM.source_field_id == source_field_id,
                ReferenceEvidenceAssertionORM.form == form.value,
            )
            .order_by(ReferenceEvidenceAssertionORM.version_number.desc())
            .first()
        )
        return None if model is None else _assertion_to_domain(model)

    def find_active_assertions_for_subject(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
    ) -> tuple[ReferenceEvidenceAssertion, ...]:
        """CDD-048 §8, §16: every ACTIVE assertion (any form) for this
        subject -- the "qualifying Reference Evidence" set an Accuracy
        evaluation may compare against, and the exact set conflict
        detection inspects for disagreement. An inactive/superseded
        assertion never appears here."""
        models = (
            self.session.query(ReferenceEvidenceAssertionORM)
            .filter(
                ReferenceEvidenceAssertionORM.tenant_id == tenant_id,
                ReferenceEvidenceAssertionORM.ontology_element_type == ontology_element_type.value,
                ReferenceEvidenceAssertionORM.ontology_element_id == ontology_element_id,
                ReferenceEvidenceAssertionORM.source_field_id == source_field_id,
                ReferenceEvidenceAssertionORM.status == ReferenceEvidenceStatus.ACTIVE.value,
            )
            .order_by(ReferenceEvidenceAssertionORM.form)
            .all()
        )
        return tuple(_assertion_to_domain(model) for model in models)

    # ------------------------------------------------------------------
    # Conflict persistence (CDD-048 §16).
    # ------------------------------------------------------------------

    def get_conflict(self, conflict_id: UUID) -> OqiReferenceEvidenceConflict | None:
        model = self.session.get(OqiReferenceEvidenceConflictORM, conflict_id)
        if model is None:
            return None
        return self._conflict_to_domain(model)

    def upsert_conflict(self, conflict: OqiReferenceEvidenceConflict) -> None:
        model = self.session.get(OqiReferenceEvidenceConflictORM, conflict.conflict_id)
        if model is None:
            self.session.add(
                OqiReferenceEvidenceConflictORM(
                    conflict_id=conflict.conflict_id,
                    tenant_id=conflict.tenant_id,
                    ontology_element_type=conflict.ontology_element_type.value,
                    ontology_element_id=conflict.ontology_element_id,
                    source_field_id=conflict.source_field_id,
                    status=conflict.status.value,
                    first_detected_at=conflict.first_detected_at,
                    last_observed_at=conflict.last_observed_at,
                )
            )
            self.session.flush()
            for assertion_id in conflict.conflicting_assertion_ids:
                self.session.add(
                    OqiReferenceEvidenceConflictMemberORM(
                        conflict_id=conflict.conflict_id, assertion_id=assertion_id
                    )
                )
            return
        model.status = conflict.status.value
        model.last_observed_at = conflict.last_observed_at

    def find_active_conflict_for_subject(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
    ) -> OqiReferenceEvidenceConflict | None:
        model = (
            self.session.query(OqiReferenceEvidenceConflictORM)
            .filter(
                OqiReferenceEvidenceConflictORM.tenant_id == tenant_id,
                OqiReferenceEvidenceConflictORM.ontology_element_type
                == ontology_element_type.value,
                OqiReferenceEvidenceConflictORM.ontology_element_id == ontology_element_id,
                OqiReferenceEvidenceConflictORM.source_field_id == source_field_id,
                OqiReferenceEvidenceConflictORM.status
                == ReferenceEvidenceConflictStatus.ACTIVE.value,
            )
            .one_or_none()
        )
        return None if model is None else self._conflict_to_domain(model)

    def _conflict_to_domain(
        self, model: OqiReferenceEvidenceConflictORM
    ) -> OqiReferenceEvidenceConflict:
        member_ids = (
            self.session.execute(
                select(OqiReferenceEvidenceConflictMemberORM.assertion_id).where(
                    OqiReferenceEvidenceConflictMemberORM.conflict_id == model.conflict_id
                )
            )
            .scalars()
            .all()
        )
        return OqiReferenceEvidenceConflict(
            conflict_id=model.conflict_id,
            tenant_id=model.tenant_id,
            ontology_element_type=OntologyElementType(model.ontology_element_type),
            ontology_element_id=model.ontology_element_id,
            source_field_id=model.source_field_id,
            conflicting_assertion_ids=tuple(sorted(member_ids, key=str)),
            status=ReferenceEvidenceConflictStatus(model.status),
            first_detected_at=model.first_detected_at,
            last_observed_at=model.last_observed_at,
        )


def _assertion_to_domain(model: ReferenceEvidenceAssertionORM) -> ReferenceEvidenceAssertion:
    return ReferenceEvidenceAssertion(
        assertion_id=model.assertion_id,
        tenant_id=model.tenant_id,
        ontology_element_type=OntologyElementType(model.ontology_element_type),
        ontology_element_id=model.ontology_element_id,
        source_field_id=model.source_field_id,
        form=ReferenceEvidenceForm(model.form),
        asserted_value=model.asserted_value,
        status=ReferenceEvidenceStatus(model.status),
        version_number=model.version_number,
        previous_version_id=model.previous_version_id,
        created_by=model.created_by,
        created_on=model.created_on,
        retired_on=model.retired_on,
    )
