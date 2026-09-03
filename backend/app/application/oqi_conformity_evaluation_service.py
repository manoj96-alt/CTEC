"""OQI-H3 deterministic Conformity evaluation orchestration (CDD-049 §8,
§14). Mirrors `OqiAccuracyEvaluationService`'s exact ordering discipline
(CDD-039 §24-§25, CDD-048 §7): derive the canonical Finding-identity material
-> acquire the transaction-scoped advisory authority -> only then select
evidence -> resolve the applicable `CanonicalStandard` via the evaluating
rule's own `information_element_requirement_id` (never a `SourceField`
fallback, PO-H3-01) -> canonicalize -> compare -> persist the immutable
ledger row idempotently -> mutate `QualityFinding` and pin the consulted
`CanonicalStandard` value/version only when the ledger insert was genuinely
new.

Unlike Accuracy, Conformity requires NO enterprise-entity resolution step --
its anchor is the rule's own `information_element_requirement_id`, resolved
directly, deterministically, with no fallback of any kind (CDD-049 §8).

NOT_EVALUABLE (CDD-049 §14) is produced -- zero persisted row -- whenever: no
observed value exists at all (Completeness's domain, never a Conformity
Finding); no ACTIVE `CanonicalStandard` exists for the rule's Information
Element (`NO_STANDARD`); the observed representation is unrecognized
(`NOT_MAPPED`); or resolution is ambiguous (`AMBIGUOUS`, defensive only --
CDD-049 §11/§12 make this structurally impossible under normal operation).

Never infers Conformity from source authority, majority, agreement, Validity,
Accuracy, LLM judgment, agent output, or anomaly score, and never imports
from `app.domain.identity_resolution` -- the canonicalization result below is
the ONLY logic that ever decides SATISFIED/VIOLATED."""

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
from app.domain.oqi_canonical_standard.standard import (
    CanonicalizationState,
    CanonicalStandard,
    canonicalize,
)
from app.domain.shared.exceptions import DomainException


class OqiConformityEvaluationError(DomainException):
    """Base exception for Conformity evaluation-orchestration failures."""


class OqiConformityRuleNotActiveError(OqiConformityEvaluationError):
    """Mirrors `OqiAccuracyRuleNotActiveError` -- raised before any
    authority is acquired or any evidence is selected."""


class OqiConformityWrongDimensionError(OqiConformityEvaluationError):
    """Raised if this service is ever invoked with a rule whose dimension
    is not CONFORMITY -- fails closed rather than silently evaluating under
    the wrong dimension's semantics."""


class ConformityEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...

    def get_finding(self, finding_id: UUID) -> QualityFinding | None: ...

    def insert_evaluation_idempotent(self, evaluation: QualityEvaluation) -> bool: ...

    def link_canonical_standard(
        self, *, evaluation_id: UUID, canonical_value_id: UUID, standard_version: int
    ) -> None: ...

    def upsert_finding(self, finding: QualityFinding) -> None: ...


class CanonicalStandardLookup(Protocol):
    def get_active_standard_for_information_element(
        self, *, information_element_requirement_id: UUID
    ) -> CanonicalStandard | None: ...


class OqiConformityEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: ConformityEvaluationRepository,
        canonical_standard_lookup: CanonicalStandardLookup,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._canonical_standard_lookup = canonical_standard_lookup
        self._clock = clock

    def evaluate_current_state(
        self, *, rule: QualityRule, subject: EvaluationSubject
    ) -> QualityEvaluation | None:
        if rule.dimension is not QualityDimension.CONFORMITY:
            raise OqiConformityWrongDimensionError(
                f"OqiConformityEvaluationService requires dimension=CONFORMITY, got {rule.dimension!r}"
            )
        if rule.status is not QualityRuleStatus.ACTIVE:
            raise OqiConformityRuleNotActiveError(
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
            # NOT_EVALUABLE: no observed value at all -- Completeness's
            # domain, never a Conformity Finding (CDD-049 §14). Zero row.
            return None
        evidence_id, observed_value = latest

        # CDD-049 §8: the ONLY resolution path -- the evaluating rule's own
        # information_element_requirement_id. No SourceField fallback, no
        # inference, no ER normalization. An unparseable value (a
        # non-UUID free-text identifier, per OQI-H3-I-R1 amendment §4)
        # means no real Information Element can be resolved -- exactly the
        # NO_STANDARD case, never a crash.
        try:
            information_element_id: UUID | None = UUID(rule.information_element_requirement_id)
        except ValueError:
            information_element_id = None
        standard = (
            None
            if information_element_id is None
            else self._canonical_standard_lookup.get_active_standard_for_information_element(
                information_element_requirement_id=information_element_id
            )
        )
        result = canonicalize(standard=standard, observed_representation=observed_value)

        if result.resolution_state in (
            CanonicalizationState.NOT_MAPPED,
            CanonicalizationState.AMBIGUOUS,
            CanonicalizationState.NO_STANDARD,
        ):
            # NOT_EVALUABLE: canonicalization could not resolve. Zero row --
            # never a fabricated pass, never a fabricated Finding (CDD-049
            # §14).
            return None

        outcome = (
            EvaluationOutcome.SATISFIED
            if result.resolution_state is CanonicalizationState.CANONICAL
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
            assert result.canonical_value_id is not None
            assert result.standard_version is not None
            self._evaluation_repository.link_canonical_standard(
                evaluation_id=evaluation.evaluation_id,
                canonical_value_id=result.canonical_value_id,
                standard_version=result.standard_version,
            )
            if next_finding is not None:
                self._evaluation_repository.upsert_finding(next_finding)
        return evaluation
