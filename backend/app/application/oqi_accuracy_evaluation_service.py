"""OQI-H2 deterministic Accuracy evaluation orchestration (CDD-048 §6-§8).
Mirrors `OqiQualityEvaluationService`'s exact ordering discipline (CDD-039
§24-§25): derive the canonical Finding-identity material -> acquire the
transaction-scoped advisory authority -> only then select evidence -> resolve
the observation's real-world identity anchor -> select qualifying Reference
Evidence -> compare -> persist the immutable ledger row idempotently ->
mutate `QualityFinding` and pin the consulted Reference Evidence only when
the ledger insert was genuinely new.

NOT_EVALUABLE (CDD-048 §6, §16) is produced -- zero persisted row, exactly
mirroring every other OQI evaluator's precedent -- whenever: no observed
value exists at all; the observation's source object has no resolved
enterprise-entity identity; or the resolved subject has no qualifying
Reference Evidence (none, or conflicting -- CDD-048 §16's `NOT_EVALUABLE`
resolution for reference-evidence conflict is achieved for free here, since
`OqiReferenceEvidenceService.get_single_qualifying_value` already returns
`None` whenever more than one distinct value is ACTIVE for the subject).

Never infers Accuracy from source authority, majority, agreement,
canonicalization, Validity, LLM judgment, agent output, or anomaly score --
the comparison below is the ONLY logic that ever decides SATISFIED/VIOLATED,
and it consults nothing but the one qualifying observed value and the one
qualifying Reference Evidence value."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domain.oqi.evaluation import (
    EvaluationMode,
    EvaluationOrigin,
    EvaluationOutcome,
    EvaluationSubject,
    QualityEvaluation,
    canonical_subject_identity,
    derive_evaluation_id,
    derive_quality_finding_id,
    evidence_set_digest,
    finding_identity_material,
)
from app.domain.oqi.finding import QualityFinding, apply_transition
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityRule,
    QualityRuleStatus,
    validate_rule_shape,
)
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_reference_evidence.assertion import ReferenceEvidenceAssertion
from app.domain.shared.exceptions import DomainException


class OqiAccuracyEvaluationError(DomainException):
    """Base exception for Accuracy evaluation-orchestration failures."""


class OqiAccuracyRuleNotActiveError(OqiAccuracyEvaluationError):
    """Mirrors `OqiRuleNotActiveError` (CDD-039 §18) -- raised before any
    authority is acquired or any evidence is selected."""


class OqiAccuracyWrongDimensionError(OqiAccuracyEvaluationError):
    """Raised if this service is ever invoked with a rule whose dimension
    is not ACCURACY -- fails closed rather than silently evaluating under
    the wrong dimension's semantics."""


class AccuracyEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def resolve_enterprise_entity_id(
        self, *, tenant_id: str, source_object_id: UUID
    ) -> UUID | None: ...

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...

    def get_finding(self, finding_id: UUID) -> QualityFinding | None: ...

    def insert_evaluation_idempotent(self, evaluation: QualityEvaluation) -> bool: ...

    def link_reference_evidence(self, *, evaluation_id: UUID, assertion_id: UUID) -> None: ...

    def upsert_finding(self, finding: QualityFinding) -> None: ...


class ReferenceEvidenceLookup(Protocol):
    def get_single_qualifying_value(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_field_id: UUID,
    ) -> tuple[str, tuple[ReferenceEvidenceAssertion, ...]] | None: ...


class OqiAccuracyEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: AccuracyEvaluationRepository,
        reference_evidence_lookup: ReferenceEvidenceLookup,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._reference_evidence_lookup = reference_evidence_lookup
        self._clock = clock

    def evaluate_current_state(
        self, *, rule: QualityRule, subject: EvaluationSubject
    ) -> QualityEvaluation | None:
        if rule.dimension is not QualityDimension.ACCURACY:
            raise OqiAccuracyWrongDimensionError(
                f"OqiAccuracyEvaluationService requires dimension=ACCURACY, got {rule.dimension!r}"
            )
        if rule.status is not QualityRuleStatus.ACTIVE:
            raise OqiAccuracyRuleNotActiveError(
                f"quality_condition_id {rule.quality_condition_id!r} has no ACTIVE version "
                "eligible for CURRENT_STATE evaluation"
            )
        # CDD-039 §33 point 3 precedent: defensive re-validation of
        # whatever persisted rule shape was loaded, immediately before use.
        validate_rule_shape(
            dimension=rule.dimension,
            finding_type=rule.finding_type,
            validity_primitive=rule.validity_primitive,
            rule_parameters=rule.rule_parameters,
        )

        horizon = self._clock()
        subject_identity = canonical_subject_identity(subject)
        identity_material = finding_identity_material(
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            subject_type=subject.subject_type,
            subject_identity=subject_identity,
        )
        # CDD-039 §24-§25 precedent: authority MUST be acquired before
        # evidence selection.
        self._evaluation_repository.acquire_evaluation_authority(identity_material)

        latest = self._evaluation_repository.select_latest_target_field_value(
            source_field_id=subject.source_field_id,
            source_record_reference=subject.lineage.source_record_reference,
            evaluation_horizon=horizon,
        )
        if latest is None:
            # NOT_EVALUABLE: no observed value at all. Zero row.
            return None
        evidence_id, observed_value = latest

        entity_id = self._evaluation_repository.resolve_enterprise_entity_id(
            tenant_id=subject.lineage.tenant_id,
            source_object_id=subject.lineage.source_object_id,
        )
        if entity_id is None:
            # NOT_EVALUABLE: no resolved real-world identity to anchor
            # Reference Evidence lookup against. Zero row.
            return None

        qualifying = self._reference_evidence_lookup.get_single_qualifying_value(
            tenant_id=subject.lineage.tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=subject.source_field_id,
        )
        if qualifying is None:
            # NOT_EVALUABLE: no qualifying Reference Evidence exists, OR
            # qualifying Reference Evidence conflicts (CDD-048 §16 -- the
            # lookup itself returns None for both cases, never inventing a
            # precedence). Zero row.
            return None
        reference_value, backing_assertions = qualifying

        outcome = (
            EvaluationOutcome.SATISFIED
            if observed_value == reference_value
            else EvaluationOutcome.VIOLATED
        )

        finding_id = derive_quality_finding_id(
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            subject_type=subject.subject_type,
            subject_identity=subject_identity,
        )
        existing_finding = self._evaluation_repository.get_finding(finding_id)
        next_finding = apply_transition(
            existing=existing_finding,
            outcome=outcome,
            evaluation_horizon=horizon,
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            subject=subject,
            finding_type=rule.finding_type,
        )

        digest = evidence_set_digest((evidence_id,))
        evaluation = QualityEvaluation(
            evaluation_id=derive_evaluation_id(
                tenant_id=subject.lineage.tenant_id,
                quality_condition_id=rule.quality_condition_id,
                rule_version=rule.version,
                subject_type=subject.subject_type,
                subject_identity=subject_identity,
                evaluation_mode=EvaluationMode.CURRENT_STATE,
                evaluation_horizon=horizon,
                evidence_digest=digest,
            ),
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            subject=subject,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_origin=EvaluationOrigin.RULE_DETERMINISTIC,
            evaluation_horizon=horizon,
            evidence_ids=(evidence_id,),
            outcome=outcome,
            applied_current_state_authority=True,
            state_revision_applied=(None if next_finding is None else next_finding.state_revision),
            evaluated_on=self._clock(),
        )

        # CDD-039 §20 precedent: idempotent replay -- a byte-identical
        # logical replay is a no-op, never a duplicate row and never a
        # second Finding mutation.
        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(evaluation)
        if newly_inserted:
            for assertion in sorted(backing_assertions, key=lambda a: str(a.assertion_id)):
                self._evaluation_repository.link_reference_evidence(
                    evaluation_id=evaluation.evaluation_id, assertion_id=assertion.assertion_id
                )
            if next_finding is not None:
                self._evaluation_repository.upsert_finding(next_finding)
        return evaluation
