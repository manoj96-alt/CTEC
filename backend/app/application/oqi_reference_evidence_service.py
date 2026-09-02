"""OQI-H2 Reference Evidence configuration, human-verification recording,
and conflict detection orchestration (CDD-048 §15-§16, §26).

Authority boundaries (CDD-048 §17, §26, PO-03): `assert_governed_reference_
dataset`/`revoke_human_verified_evidence` are configuration-authority
operations (`oqi-reference-evidence:configure`); `record_human_verified_
evidence` is a distinct, non-substitutable verification-authority operation
(`oqi-reference-evidence:verify`) -- this service enforces neither scope
itself (that is the API layer's responsibility, mirroring every other OQI
service), but its method boundaries are drawn exactly along this authority
split so the API layer can never accidentally gate the wrong operation
behind the wrong scope.

Conflict detection (CDD-048 §16) never invents a truth-selection rule: two
or more ACTIVE assertions for the same subject with differing
`asserted_value` opens (or touches) a governance conflict; a subject with
zero or one distinct asserted value among its ACTIVE assertions has no
conflict (or resolves an existing one)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_reference_evidence.assertion import (
    BusinessRuleDerivedReferenceEntry,
    GovernedReferenceDatasetEntry,
    HumanVerifiedEvidenceEntry,
    ReferenceEvidenceAssertion,
    ReferenceEvidenceForm,
    activate_new_assertion_version,
)
from app.domain.oqi_reference_evidence.conflict import (
    OqiReferenceEvidenceConflict,
    open_or_touch_conflict,
    resolve_conflict,
)
from app.domain.shared.exceptions import DomainException
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)

_IDENTITY_ALGORITHM_VERSION = "OQI_REFERENCE_EVIDENCE_AUTHORITY_V1"


class OqiReferenceEvidenceError(DomainException):
    """Carries one of this module's closed diagnostic codes."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _authority_identity(
    *,
    tenant_id: str,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    source_field_id: UUID,
    form: ReferenceEvidenceForm,
) -> str:
    from app.domain.oqi.evaluation import _length_prefixed, canonical_form

    return (
        _length_prefixed(_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(ontology_element_type.value)
        + _length_prefixed(canonical_form(ontology_element_id))
        + _length_prefixed(canonical_form(source_field_id))
        + _length_prefixed(form.value)
    )


class OqiReferenceEvidenceService:
    def __init__(
        self,
        *,
        repository: OqiReferenceEvidenceRepositoryImpl,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._clock = clock

    def _activate(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
        form: ReferenceEvidenceForm,
        asserted_value: str,
        created_by: str,
        now: datetime,
    ) -> ReferenceEvidenceAssertion:
        identity = _authority_identity(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            form=form,
        )
        self._repository.acquire_reference_evidence_authority(identity)

        existing_active = self._repository.get_active_assertion(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            form=form,
        )
        new_version = activate_new_assertion_version(
            existing_active=existing_active,
            assertion_id=uuid4(),
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            form=form,
            asserted_value=asserted_value,
            created_by=created_by,
            created_on=now,
        )
        if existing_active is not None:
            self._repository.retire_assertion(
                assertion_id=existing_active.assertion_id, retired_on=now
            )
        self._repository.insert_assertion(new_version)
        return new_version

    def assert_governed_reference_dataset(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
        asserted_value: str,
        dataset_name: str,
        dataset_version: str,
        entry_key: str,
        created_by: str,
        now: datetime | None = None,
    ) -> ReferenceEvidenceAssertion:
        """Configuration-authority operation (CDD-048 §26,
        `oqi-reference-evidence:configure`). The dataset itself remains
        shared-platform (PO-02) -- this call records only the tenant's
        assertion that a governed dataset entry applies to its subject."""
        moment = now if now is not None else self._clock()
        assertion = self._activate(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            form=ReferenceEvidenceForm.GOVERNED_REFERENCE_DATASET,
            asserted_value=asserted_value,
            created_by=created_by,
            now=moment,
        )
        self._repository.insert_governed_reference_dataset_entry(
            GovernedReferenceDatasetEntry(
                assertion_id=assertion.assertion_id,
                dataset_name=dataset_name,
                dataset_version=dataset_version,
                entry_key=entry_key,
            )
        )
        self.detect_conflict_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            now=moment,
        )
        return assertion

    def record_human_verified_evidence(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
        asserted_value: str,
        verifying_actor_id: str,
        verification_rationale: str,
        created_by: str,
        now: datetime | None = None,
    ) -> ReferenceEvidenceAssertion:
        """Verification-authority operation (CDD-048 §17, §26,
        `oqi-reference-evidence:verify`, PO-03) -- distinct from and never
        substitutable by configuration or remediation authority. Human
        verification is governed evidence, not absolute truth: it
        participates in Accuracy comparisons and conflict detection exactly
        like the other two forms."""
        moment = now if now is not None else self._clock()
        assertion = self._activate(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            form=ReferenceEvidenceForm.HUMAN_VERIFIED_EVIDENCE,
            asserted_value=asserted_value,
            created_by=created_by,
            now=moment,
        )
        self._repository.insert_human_verified_evidence_entry(
            HumanVerifiedEvidenceEntry(
                assertion_id=assertion.assertion_id,
                verifying_actor_id=verifying_actor_id,
                verification_timestamp=moment,
                verification_rationale=verification_rationale,
            )
        )
        self.detect_conflict_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            now=moment,
        )
        return assertion

    def revoke_human_verified_evidence(
        self, *, assertion_id: UUID, now: datetime | None = None
    ) -> None:
        """CDD-048 §27: revocation supersedes without rewriting history --
        historical Accuracy evaluations that pinned this exact assertion
        version remain, permanently, an honest record of what was
        supportable at their own evaluation time. Retires the assertion
        itself (a new HUMAN_VERIFIED_EVIDENCE version may follow via a
        fresh `record_human_verified_evidence` call, an entirely separate,
        later governed act)."""
        moment = now if now is not None else self._clock()
        self._repository.retire_assertion(assertion_id=assertion_id, retired_on=moment)

    def record_business_rule_derived_reference(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
        asserted_value: str,
        deriving_business_rule_id: UUID,
        deriving_rule_version: int,
        deriving_evaluation_id: UUID,
        created_by: str,
        now: datetime | None = None,
    ) -> ReferenceEvidenceAssertion:
        """CDD-048 §18: pins the exact deterministic `BusinessRuleEvaluation`
        that produced `asserted_value` -- no probabilistic or LLM-produced
        value may ever back this form (enforced structurally: the caller
        must already hold a real, immutable evaluation id, which only
        OQI3's deterministic evaluator ever produces)."""
        moment = now if now is not None else self._clock()
        assertion = self._activate(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            form=ReferenceEvidenceForm.BUSINESS_RULE_DERIVED_VALUE,
            asserted_value=asserted_value,
            created_by=created_by,
            now=moment,
        )
        self._repository.insert_business_rule_derived_reference_entry(
            BusinessRuleDerivedReferenceEntry(
                assertion_id=assertion.assertion_id,
                deriving_business_rule_id=deriving_business_rule_id,
                deriving_rule_version=deriving_rule_version,
                deriving_evaluation_id=deriving_evaluation_id,
            )
        )
        self.detect_conflict_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            now=moment,
        )
        return assertion

    def detect_conflict_for_subject(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
        now: datetime | None = None,
    ) -> OqiReferenceEvidenceConflict | None:
        """CDD-048 §16: re-derives whether the subject's currently-ACTIVE
        assertions (any form) disagree. Never invents a precedence between
        them. Returns the conflict row if one is ACTIVE after this call,
        else `None`."""
        moment = now if now is not None else self._clock()
        active_assertions = self._repository.find_active_assertions_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
        )
        distinct_values = {assertion.asserted_value for assertion in active_assertions}
        existing_conflict = self._repository.find_active_conflict_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
        )

        if len(distinct_values) <= 1:
            if existing_conflict is not None:
                resolved = resolve_conflict(existing=existing_conflict, now=moment)
                self._repository.upsert_conflict(resolved)
            return None

        conflicting_ids = tuple(
            sorted((assertion.assertion_id for assertion in active_assertions), key=str)
        )
        conflict = open_or_touch_conflict(
            existing=existing_conflict,
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
            conflicting_assertion_ids=conflicting_ids,
            now=moment,
        )
        self._repository.upsert_conflict(conflict)
        return conflict

    def has_qualifying_reference_evidence(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
    ) -> bool:
        """A subject qualifies for Accuracy evaluation only when it has at
        least one ACTIVE assertion AND no unresolved conflict among them
        (CDD-048 §8, §16 -- conflicting qualifying evidence yields
        NOT_EVALUABLE, never a fabricated comparison)."""
        active_assertions = self._repository.find_active_assertions_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
        )
        if not active_assertions:
            return False
        distinct_values = {assertion.asserted_value for assertion in active_assertions}
        return len(distinct_values) == 1

    def get_single_qualifying_value(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
    ) -> tuple[str, tuple[ReferenceEvidenceAssertion, ...]] | None:
        """Returns `(asserted_value, backing_assertions)` when exactly one
        distinct value is asserted by the subject's ACTIVE assertions
        (regardless of how many forms agree on it), else `None`
        (NOT_EVALUABLE: no qualifying evidence, or qualifying evidence
        conflicts)."""
        active_assertions = self._repository.find_active_assertions_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_field_id=source_field_id,
        )
        if not active_assertions:
            return None
        distinct_values = {assertion.asserted_value for assertion in active_assertions}
        if len(distinct_values) != 1:
            return None
        value = next(iter(distinct_values))
        return value, active_assertions
