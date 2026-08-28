"""OQI deterministic quality-evaluation orchestration service (CDD-039
§19, §22-§25, §33; OQI1 Artifact Authorization §4; Concurrency Hardening
Amendment §11). `evaluate_historical` never acquires evaluation authority
and never touches `QualityFinding` (CDD-039 §22). `evaluate_current_state`
enforces the non-negotiable ordering: derive the canonical Finding-identity
material -> acquire the transaction-scoped advisory authority -> only then
select evidence -> evaluate -> persist the immutable ledger row
idempotently -> mutate `QualityFinding` only when the ledger insert was
genuinely new (CDD-039 §24-§25, §20). Neither method ever executes user
code, calls an LLM, or otherwise determines quality truth by any means
other than the deterministic rule primitives in `app.domain.oqi.evaluation`
(CDD-039 §19, "RULE_DETERMINISTIC" origin)."""

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
    evaluate_completeness,
    evaluate_validity,
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
from app.domain.shared.exceptions import DomainException, ValidationException


class OqiEvaluationError(DomainException):
    """Base exception for OQI evaluation-orchestration failures."""


class OqiRuleNotActiveError(OqiEvaluationError):
    """CDD-039 §18: "If no ACTIVE version exists for a quality_condition_id,
    CURRENT_STATE evaluation is ineligible." Raised before any authority is
    acquired or any evidence is selected."""


class RuleRepository(Protocol):
    def get_active(self, quality_condition_id: str) -> QualityRule | None: ...


class EvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> QualityFinding | None: ...

    def insert_evaluation_idempotent(self, evaluation: QualityEvaluation) -> bool: ...

    def upsert_finding(self, finding: QualityFinding) -> None: ...

    def select_known_lineage_evidence_id(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> UUID | None: ...

    def select_target_field_evidence_ids(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, ...]: ...

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...


class OqiQualityEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: EvaluationRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._clock = clock

    def evaluate_historical(
        self,
        *,
        rule: QualityRule,
        subject: EvaluationSubject,
        evaluation_horizon: datetime,
    ) -> QualityEvaluation | None:
        """CDD-039 §22: caller-supplied horizon; persists its own ledger
        row when an evaluation is possible; never acquires authority; never
        creates, opens, resolves, or reopens a `QualityFinding`; never
        touches `state_revision`/`occurrence_count`/`reopen_count`."""
        if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")

        outcome_and_evidence = self._select_evidence_and_evaluate(
            rule=rule, subject=subject, evaluation_horizon=evaluation_horizon
        )
        if outcome_and_evidence is None:
            return None
        outcome, evidence_ids = outcome_and_evidence

        subject_identity = canonical_subject_identity(subject)
        digest = evidence_set_digest(evidence_ids)
        evaluation = QualityEvaluation(
            evaluation_id=derive_evaluation_id(
                tenant_id=subject.lineage.tenant_id,
                quality_condition_id=rule.quality_condition_id,
                rule_version=rule.version,
                subject_type=subject.subject_type,
                subject_identity=subject_identity,
                evaluation_mode=EvaluationMode.HISTORICAL,
                evaluation_horizon=evaluation_horizon,
                evidence_digest=digest,
            ),
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            subject=subject,
            evaluation_mode=EvaluationMode.HISTORICAL,
            evaluation_origin=EvaluationOrigin.RULE_DETERMINISTIC,
            evaluation_horizon=evaluation_horizon,
            evidence_ids=evidence_ids,
            outcome=outcome,
            applied_current_state_authority=False,
            state_revision_applied=None,
            evaluated_on=self._clock(),
        )
        self._evaluation_repository.insert_evaluation_idempotent(evaluation)
        return evaluation

    def evaluate_current_state(
        self, *, rule: QualityRule, subject: EvaluationSubject
    ) -> QualityEvaluation | None:
        """CDD-039 §18, §23-§25: the trusted runtime clock supplies the
        horizon; authority is acquired before evidence selection; the
        ledger insert is idempotent; `QualityFinding` is mutated only when
        the ledger insert was genuinely new."""
        if rule.status is not QualityRuleStatus.ACTIVE:
            raise OqiRuleNotActiveError(
                f"quality_condition_id {rule.quality_condition_id!r} has no ACTIVE version "
                "eligible for CURRENT_STATE evaluation"
            )

        horizon = self._clock()
        subject_identity = canonical_subject_identity(subject)
        identity_material = finding_identity_material(
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            subject_type=subject.subject_type,
            subject_identity=subject_identity,
        )
        # CDD-039 §24-§25: authority MUST be acquired before evidence
        # selection -- this is the very next line, unconditionally.
        self._evaluation_repository.acquire_evaluation_authority(identity_material)

        outcome_and_evidence = self._select_evidence_and_evaluate(
            rule=rule, subject=subject, evaluation_horizon=horizon
        )
        if outcome_and_evidence is None:
            # Unknown lineage (Completeness) or no qualifying value
            # (Validity): no evaluation, no Finding touched. Authority
            # releases automatically on commit/rollback.
            return None
        outcome, evidence_ids = outcome_and_evidence

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

        digest = evidence_set_digest(evidence_ids)
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
            evidence_ids=evidence_ids,
            outcome=outcome,
            applied_current_state_authority=True,
            state_revision_applied=(None if next_finding is None else next_finding.state_revision),
            evaluated_on=self._clock(),
        )

        # CDD-039 §20: idempotent replay -- if this exact evaluation_id
        # already exists, the ledger insert is a no-op and the Finding
        # (already correctly mutated by the original application) MUST NOT
        # be mutated a second time.
        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(evaluation)
        if newly_inserted and next_finding is not None:
            self._evaluation_repository.upsert_finding(next_finding)
        return evaluation

    def _select_evidence_and_evaluate(
        self, *, rule: QualityRule, subject: EvaluationSubject, evaluation_horizon: datetime
    ) -> tuple[EvaluationOutcome, tuple[UUID, ...]] | None:
        """Returns `(outcome, evidence_ids)` or `None` when no evaluation
        is possible: unknown lineage (Completeness, CDD-039 §12) or no
        qualifying target value (Validity, CDD-039 §32 -- missingness
        belongs exclusively to Completeness)."""
        # CDD-039 §33 point 3: defensive re-validation of whatever
        # persisted rule shape was loaded, immediately before use. Only
        # reachable via out-of-band database corruption, since every
        # governed write path (construction, create/activate) already
        # enforces this -- but evaluation must still fail closed with the
        # typed error rather than let a raw KeyError/TypeError escape from
        # a malformed `rule_parameters` dict.
        validate_rule_shape(
            dimension=rule.dimension,
            finding_type=rule.finding_type,
            validity_primitive=rule.validity_primitive,
            rule_parameters=rule.rule_parameters,
        )
        if rule.dimension is QualityDimension.COMPLETENESS:
            known = self._evaluation_repository.select_known_lineage_evidence_id(
                source_object_id=subject.lineage.source_object_id,
                source_record_reference=subject.lineage.source_record_reference,
                evaluation_horizon=evaluation_horizon,
            )
            if known is None:
                return None
            target_ids = self._evaluation_repository.select_target_field_evidence_ids(
                source_field_id=subject.source_field_id,
                source_record_reference=subject.lineage.source_record_reference,
                evaluation_horizon=evaluation_horizon,
            )
            outcome = evaluate_completeness(qualifying_target_evidence_ids=target_ids)
            return outcome, tuple(sorted(target_ids, key=str))

        # VALIDITY
        latest = self._evaluation_repository.select_latest_target_field_value(
            source_field_id=subject.source_field_id,
            source_record_reference=subject.lineage.source_record_reference,
            evaluation_horizon=evaluation_horizon,
        )
        if latest is None:
            return None
        evidence_id, value = latest
        assert rule.validity_primitive is not None
        outcome = evaluate_validity(
            primitive=rule.validity_primitive, value=value, rule_parameters=rule.rule_parameters
        )
        return outcome, (evidence_id,)
