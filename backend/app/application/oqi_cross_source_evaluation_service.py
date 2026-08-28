"""OQI2 cross-source deterministic evaluation orchestration service
(CDD-040 §14-§50). Mirrors `OqiQualityEvaluationService`'s proven
discipline exactly: `evaluate_historical` never acquires authority and
never touches `QualityComparisonFinding`; `evaluate_current_state` enforces
the frozen ordering (CDD-040 §46) -- load ACTIVE rule + ACTIVE
correspondence -> defensive in-memory status checks -> compute Finding-
identity material -> acquire authority -> select per-participant evidence
-> evaluate -> persist idempotently -> mutate Finding only when genuinely
new. Never executes user code, calls an LLM, or otherwise determines
cross-source truth by any means other than the deterministic exact-match
primitive in `app.domain.oqi_cross_source.evaluation` (CDD-040 §25, §43).

Implements CDD-040 §27/§29's full epistemic missingness resolution: a role
absent from the ACTIVE correspondence is never evaluated regardless of the
rule's `expected` flag (§27 case 4b); a role the correspondence names but
whose lineage is unknown is a genuine missing-participant Finding only when
the rule also marks it `expected=true` (§27 case 4a) -- rule-level
`expected` alone is never sufficient."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domain.oqi.evaluation import (
    EvaluationMode,
    EvaluationOrigin,
    EvaluationOutcome,
    SourceRecordLineageIdentity,
)
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.oqi_cross_source.evaluation import (
    ParticipantEvidenceEntry,
    QualityComparisonEvaluation,
    derive_comparison_evaluation_id,
    derive_comparison_finding_id,
    evaluate_consistency,
    finding_identity_material,
    participant_evidence_digest,
)
from app.domain.oqi_cross_source.finding import (
    QualityComparisonFinding,
    apply_correspondence_finding_transition,
)
from app.domain.shared.exceptions import DomainException, ValidationException


class OqiCrossSourceEvaluationError(DomainException):
    """Base exception for OQI2 evaluation-orchestration failures."""


class OqiRuleNotActiveError(OqiCrossSourceEvaluationError):
    """CDD-040 §45: no ACTIVE rule version -> CURRENT_STATE evaluation is
    ineligible. Raised before any authority is acquired or any evidence is
    selected."""


class OqiCorrespondenceNotActiveError(OqiCrossSourceEvaluationError):
    """CDD-040 §27, §34, §45: no ACTIVE correspondence for this comparison
    subject -> CURRENT_STATE evaluation is ineligible. Never resolves an
    existing Finding (CDD-040 §34)."""


class ParticipantEvidenceRepository(Protocol):
    def select_known_lineage(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> bool: ...

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...


class ComparisonEvaluationRepository(ParticipantEvidenceRepository, Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> QualityComparisonFinding | None: ...

    def insert_evaluation_idempotent(self, evaluation: QualityComparisonEvaluation) -> bool: ...

    def upsert_finding(self, finding: QualityComparisonFinding) -> None: ...


class OqiCrossSourceEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: ComparisonEvaluationRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._clock = clock

    def evaluate_historical(
        self,
        *,
        rule: QualityRule,
        correspondence: ComparisonSubjectCorrespondence,
        evaluation_horizon: datetime,
    ) -> QualityComparisonEvaluation | None:
        """CDD-040 §44: caller-supplied horizon; persists its own ledger
        row when an evaluation is possible; never acquires authority; never
        creates, opens, resolves, or reopens a `QualityComparisonFinding`."""
        if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")
        _assert_rule_and_correspondence_scope(rule=rule, correspondence=correspondence)

        result = self._select_participant_evidence_and_evaluate(
            rule=rule, correspondence=correspondence, evaluation_horizon=evaluation_horizon
        )
        if result is None:
            return None
        outcome, _finding_type, participants = result

        digest = participant_evidence_digest(participants)
        evaluation = QualityComparisonEvaluation(
            evaluation_id=derive_comparison_evaluation_id(
                tenant_id=correspondence.tenant_id,
                quality_condition_id=rule.quality_condition_id,
                rule_version=rule.version,
                comparison_subject_id=correspondence.comparison_subject_id,
                evaluation_mode=EvaluationMode.HISTORICAL,
                evaluation_horizon=evaluation_horizon,
                participant_digest=digest,
                comparison_subject_correspondence_id=correspondence.correspondence_id,
            ),
            tenant_id=correspondence.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            comparison_subject_id=correspondence.comparison_subject_id,
            comparison_subject_correspondence_id=correspondence.correspondence_id,
            evaluation_mode=EvaluationMode.HISTORICAL,
            evaluation_origin=EvaluationOrigin.RULE_DETERMINISTIC,
            evaluation_horizon=evaluation_horizon,
            participants=participants,
            outcome=outcome,
            applied_current_state_authority=False,
            state_revision_applied=None,
            evaluated_on=self._clock(),
        )
        self._evaluation_repository.insert_evaluation_idempotent(evaluation)
        return evaluation

    def evaluate_current_state(
        self,
        *,
        rule: QualityRule,
        correspondence: ComparisonSubjectCorrespondence,
    ) -> QualityComparisonEvaluation | None:
        """CDD-040 §45-§47: the trusted runtime clock supplies the horizon;
        both the rule and correspondence must be ACTIVE (checked against
        the caller-supplied, pre-loaded in-memory objects -- never
        re-queried after lock acquisition, mirroring OQI1 exactly);
        authority is acquired before evidence selection; the ledger insert
        is idempotent; `QualityComparisonFinding` is mutated only when the
        ledger insert was genuinely new."""
        if rule.status is not QualityRuleStatus.ACTIVE:
            raise OqiRuleNotActiveError(
                f"quality_condition_id {rule.quality_condition_id!r} has no ACTIVE version "
                "eligible for CURRENT_STATE evaluation"
            )
        if correspondence.status is not ComparisonSubjectCorrespondenceStatus.ACTIVE:
            raise OqiCorrespondenceNotActiveError(
                f"comparison_subject_id {correspondence.comparison_subject_id!r} has no ACTIVE "
                "correspondence eligible for CURRENT_STATE evaluation"
            )
        _assert_rule_and_correspondence_scope(rule=rule, correspondence=correspondence)

        horizon = self._clock()
        identity_material = finding_identity_material(
            tenant_id=correspondence.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            comparison_subject_id=correspondence.comparison_subject_id,
        )
        # CDD-040 §46-§47: authority MUST be acquired before evidence
        # selection -- this is the very next line, unconditionally.
        self._evaluation_repository.acquire_evaluation_authority(identity_material)

        result = self._select_participant_evidence_and_evaluate(
            rule=rule, correspondence=correspondence, evaluation_horizon=horizon
        )
        if result is None:
            # Fewer than 2 known-and-valued participants and no
            # deterministically-provable missingness: no evaluation, no
            # Finding touched. Authority releases automatically on
            # commit/rollback.
            return None
        outcome, finding_type, participants = result

        finding_id = derive_comparison_finding_id(
            tenant_id=correspondence.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            comparison_subject_id=correspondence.comparison_subject_id,
        )
        existing_finding = self._evaluation_repository.get_finding(finding_id)

        digest = participant_evidence_digest(participants)
        evaluation_id = derive_comparison_evaluation_id(
            tenant_id=correspondence.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            rule_version=rule.version,
            comparison_subject_id=correspondence.comparison_subject_id,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_horizon=horizon,
            participant_digest=digest,
            comparison_subject_correspondence_id=correspondence.correspondence_id,
        )
        next_finding = apply_correspondence_finding_transition(
            existing=existing_finding,
            outcome=outcome,
            evaluation_horizon=horizon,
            tenant_id=correspondence.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            comparison_subject_id=correspondence.comparison_subject_id,
            finding_type=finding_type,
            evaluation_id=evaluation_id,
        )

        evaluation = QualityComparisonEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=correspondence.tenant_id,
            quality_condition_id=rule.quality_condition_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            comparison_subject_id=correspondence.comparison_subject_id,
            comparison_subject_correspondence_id=correspondence.correspondence_id,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_origin=EvaluationOrigin.RULE_DETERMINISTIC,
            evaluation_horizon=horizon,
            participants=participants,
            outcome=outcome,
            applied_current_state_authority=True,
            state_revision_applied=(None if next_finding is None else next_finding.state_revision),
            evaluated_on=self._clock(),
        )

        # CDD-040 §43: idempotent replay -- if this exact evaluation_id
        # already exists, the ledger insert is a no-op and the Finding
        # (already correctly mutated by the original application) MUST NOT
        # be mutated a second time.
        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(evaluation)
        if newly_inserted and next_finding is not None:
            self._evaluation_repository.upsert_finding(next_finding)
        return evaluation

    def _select_participant_evidence_and_evaluate(
        self,
        *,
        rule: QualityRule,
        correspondence: ComparisonSubjectCorrespondence,
        evaluation_horizon: datetime,
    ) -> (
        tuple[EvaluationOutcome, QualityFindingType | None, tuple[ParticipantEvidenceEntry, ...]]
        | None
    ):
        """CDD-040 §27-§30's exact deterministic algorithm. Returns
        `(outcome, finding_type, participants)` or `None` when no
        evaluation is possible (fewer than 2 known-and-valued participants
        and no deterministically-provable missingness)."""
        members_by_role = {member.participant_role: member for member in correspondence.members}
        configured_participants = rule.rule_parameters["participants"]

        participants: list[ParticipantEvidenceEntry] = []
        known_values: dict[str, str] = {}
        any_missing = False

        for entry in configured_participants:
            if not entry["eligible"]:
                continue
            role = entry["role"]
            source_field_id = UUID(entry["source_field_id"])
            expected = entry["expected"]
            authoritative = entry["authoritative"]

            member = members_by_role.get(role)
            if member is None:
                # CDD-040 §27 case 4b / §29 Case 3: correspondence names no
                # lineage for this role for this subject -- excluded,
                # regardless of `expected`.
                continue

            lineage = SourceRecordLineageIdentity(
                tenant_id=correspondence.tenant_id,
                source_object_id=member.source_object_id,
                source_record_reference=member.source_record_reference,
            )
            known = self._evaluation_repository.select_known_lineage(
                source_object_id=member.source_object_id,
                source_record_reference=member.source_record_reference,
                evaluation_horizon=evaluation_horizon,
            )
            if not known:
                if expected:
                    # CDD-040 §29 Case 4: the correspondence's own naming
                    # of this lineage IS the positive, subject-level
                    # governed knowledge that justifies missingness here --
                    # not the rule's `expected` flag in isolation.
                    participants.append(
                        ParticipantEvidenceEntry(
                            role=role,
                            lineage=lineage,
                            source_field_id=source_field_id,
                            expected=expected,
                            authoritative=authoritative,
                            evidence_ids=(),
                        )
                    )
                    any_missing = True
                # else CDD-040 §29 Case 5: excluded entirely.
                continue

            latest = self._evaluation_repository.select_latest_target_field_value(
                source_field_id=source_field_id,
                source_record_reference=member.source_record_reference,
                evaluation_horizon=evaluation_horizon,
            )
            if latest is None:
                # CDD-040 §29 Cases 1/2: known lineage, zero qualifying
                # target evidence.
                participants.append(
                    ParticipantEvidenceEntry(
                        role=role,
                        lineage=lineage,
                        source_field_id=source_field_id,
                        expected=expected,
                        authoritative=authoritative,
                        evidence_ids=(),
                    )
                )
                if expected:
                    any_missing = True  # Case 1
                # else Case 2: present, informational, no missing finding.
                continue

            evidence_id, value = latest
            participants.append(
                ParticipantEvidenceEntry(
                    role=role,
                    lineage=lineage,
                    source_field_id=source_field_id,
                    expected=expected,
                    authoritative=authoritative,
                    evidence_ids=(evidence_id,),
                )
            )
            known_values[role] = value

        if any_missing:
            return (
                EvaluationOutcome.VIOLATED,
                QualityFindingType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING,
                tuple(participants),
            )

        if len(known_values) < 2:
            # CDD-040 §30: a single observed value cannot prove or disprove
            # cross-source consistency.
            return None

        outcome = evaluate_consistency(participant_values=known_values)
        finding_type = (
            QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT
            if outcome is EvaluationOutcome.VIOLATED
            else None
        )
        return outcome, finding_type, tuple(participants)


def _assert_rule_and_correspondence_scope(
    *, rule: QualityRule, correspondence: ComparisonSubjectCorrespondence
) -> None:
    if rule.dimension is not QualityDimension.CONSISTENCY:
        raise ValidationException("rule.dimension must be CONSISTENCY for cross-source evaluation")
    if "participants" not in rule.rule_parameters:
        raise ValidationException("rule.rule_parameters must contain 'participants'")
