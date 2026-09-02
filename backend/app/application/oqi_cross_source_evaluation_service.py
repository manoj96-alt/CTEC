"""OQI2 cross-source deterministic evaluation orchestration service
(CDD-040 §14-§50; N-Source Finding Representation Amendment §13). Mirrors
`OqiQualityEvaluationService`'s proven discipline exactly:
`evaluate_historical` never acquires authority and never touches
`QualityComparisonFinding`; `evaluate_current_state` enforces the frozen
ordering (CDD-040 §46) -- load ACTIVE rule + ACTIVE correspondence ->
defensive in-memory status checks -> compute Finding-identity material ->
acquire authority -> select per-participant evidence -> evaluate -> persist
idempotently -> mutate Finding only when genuinely new. Never executes user
code, calls an LLM, or otherwise determines cross-source truth by any means
other than the deterministic exact-match primitive in
`app.domain.oqi_cross_source.evaluation` (CDD-040 §25, §43).

Implements CDD-040 §27/§29's full epistemic missingness resolution: a role
absent from the ACTIVE correspondence is never evaluated regardless of the
rule's `expected` flag (§27 case 4b); a role the correspondence names but
whose lineage is unknown is a genuine missing-participant observation only
when the rule also marks it `expected=true` (§27 case 4a) -- rule-level
`expected` alone is never sufficient.

Missingness and conflict are evaluated independently and combined (amendment
§13): every deterministically-provable missing participant produces its own
`CROSS_SOURCE_PARTICIPANT_VALUE_MISSING` observation, and -- whenever two or
more known participant values exist -- an independent conflict check
produces a `CROSS_SOURCE_VALUE_CONFLICT` observation for every known
participant when they disagree. Neither computation suppresses the other,
closing the P1 where a value conflict among known participants could be
silently lost merely because another participant was also missing."""

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
from app.domain.oqi.quality_rule import QualityDimension, QualityRule, QualityRuleStatus
from app.domain.oqi_canonical_standard.standard import (
    CanonicalizationState,
    CanonicalStandard,
    canonicalize,
)
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.oqi_cross_source.evaluation import (
    ComparisonObservation,
    ComparisonObservationType,
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

#: CDD-049 §16: one row per participant successfully canonicalized and
#: consulted in a Case-B comparison -- (participant_role, canonical_value_id,
#: standard_version).
CanonicalProjectionRow = tuple[str, UUID, int]


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

    def link_canonical_projection(
        self,
        *,
        evaluation_id: UUID,
        participant_role: str,
        canonical_value_id: UUID,
        standard_version: int,
    ) -> None: ...


class CanonicalStandardLookup(Protocol):
    def get_active_standard_for_information_element(
        self, *, information_element_requirement_id: UUID
    ) -> CanonicalStandard | None: ...


class OqiCrossSourceEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: ComparisonEvaluationRepository,
        canonical_standard_lookup: CanonicalStandardLookup | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._canonical_standard_lookup = canonical_standard_lookup
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
        outcome, observations, participants, canonical_projections = result

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
            observations=observations,
        )
        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(evaluation)
        if newly_inserted:
            for role, canonical_value_id, standard_version in canonical_projections:
                self._evaluation_repository.link_canonical_projection(
                    evaluation_id=evaluation.evaluation_id,
                    participant_role=role,
                    canonical_value_id=canonical_value_id,
                    standard_version=standard_version,
                )
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
            # deterministically-provable missingness, OR a CDD-049 §16.2
            # canonicalization-failure NOT_EVALUABLE attempt with nothing
            # else to report: no evaluation, no Finding touched. Authority
            # releases automatically on commit/rollback.
            return None
        outcome, observations, participants, canonical_projections = result

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
            observations=observations,
        )

        # CDD-040 §43: idempotent replay -- if this exact evaluation_id
        # already exists, the ledger insert is a no-op and the Finding
        # (already correctly mutated by the original application) MUST NOT
        # be mutated a second time.
        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(evaluation)
        if newly_inserted:
            for role, canonical_value_id, standard_version in canonical_projections:
                self._evaluation_repository.link_canonical_projection(
                    evaluation_id=evaluation.evaluation_id,
                    participant_role=role,
                    canonical_value_id=canonical_value_id,
                    standard_version=standard_version,
                )
            if next_finding is not None:
                self._evaluation_repository.upsert_finding(next_finding)
        return evaluation

    def _select_participant_evidence_and_evaluate(
        self,
        *,
        rule: QualityRule,
        correspondence: ComparisonSubjectCorrespondence,
        evaluation_horizon: datetime,
    ) -> (
        tuple[
            EvaluationOutcome,
            tuple[ComparisonObservation, ...],
            tuple[ParticipantEvidenceEntry, ...],
            tuple[CanonicalProjectionRow, ...],
        ]
        | None
    ):
        """CDD-040 §27-§30's participant-selection algorithm, combined with
        the N-Source Finding Representation Amendment §13 replacement for
        the missingness short-circuit, combined with CDD-049 §16's governed
        canonical-projection gate. Returns `(outcome, observations,
        participants, canonical_projections)` or `None` when no evaluation
        is possible."""
        members_by_role = {member.participant_role: member for member in correspondence.members}
        configured_participants = rule.rule_parameters["participants"]

        participants: list[ParticipantEvidenceEntry] = []
        known_values: dict[str, str] = {}
        missing_roles: list[str] = []

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
                    missing_roles.append(role)
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
                    missing_roles.append(role)  # Case 1
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

        # Amendment §13 step 1: one independent missing observation per
        # deterministically-provable missing participant. Never suppressed
        # by, and never suppresses, the conflict computation below.
        observations: list[ComparisonObservation] = [
            ComparisonObservation(
                observation_type=ComparisonObservationType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING,
                participant_role=role,
            )
            for role in missing_roles
        ]

        # CDD-049 §16.1: resolve the applicable CanonicalStandard for this
        # comparison's Information Element (the rule's own
        # information_element_requirement_id -- every QualityRule of every
        # dimension carries this field, CDD-049 §8). CASE A (no standard,
        # or no lookup wired at all) leaves comparison_values as the raw
        # known_values, byte-for-byte unchanged from pre-H3 behavior.
        comparison_values: dict[str, str] = known_values
        canonicalization_failed = False
        canonical_projections: list[CanonicalProjectionRow] = []

        if len(known_values) >= 2 and self._canonical_standard_lookup is not None:
            standard = self._canonical_standard_lookup.get_active_standard_for_information_element(
                information_element_requirement_id=UUID(rule.information_element_requirement_id)
            )
            if standard is not None:
                # CASE B: every required known participant must resolve
                # under this ONE standard/version, or the value-agreement
                # sub-computation is NOT_EVALUABLE (CDD-049 §16.1).
                projected_values: dict[str, str] = {}
                for role, raw_value in known_values.items():
                    result = canonicalize(standard=standard, observed_representation=raw_value)
                    if result.resolution_state in (
                        CanonicalizationState.NOT_MAPPED,
                        CanonicalizationState.AMBIGUOUS,
                    ):
                        canonicalization_failed = True
                        break
                    assert result.resolved_canonical_value is not None
                    assert result.canonical_value_id is not None
                    assert result.standard_version is not None
                    projected_values[role] = result.resolved_canonical_value
                    canonical_projections.append(
                        (role, result.canonical_value_id, result.standard_version)
                    )
                if canonicalization_failed:
                    canonical_projections = []
                else:
                    comparison_values = projected_values

        # Amendment §13 step 2 / CDD-049 §16.1: whenever >= 2 known values
        # exist AND canonicalization did not fail, independently evaluate
        # them for disagreement -- regardless of whether any participant is
        # simultaneously missing. A canonicalization failure contributes NO
        # observation of any kind here -- CANONICALIZATION FAILURE ≠ VALUE
        # CONFLICT (CDD-049 §16, §32) -- it never fabricates a
        # CROSS_SOURCE_VALUE_CONFLICT and never falls back to raw
        # comparison.
        if len(known_values) >= 2 and not canonicalization_failed:
            consistency_outcome = evaluate_consistency(participant_values=comparison_values)
            if consistency_outcome is EvaluationOutcome.VIOLATED:
                observations.extend(
                    ComparisonObservation(
                        observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
                        participant_role=role,
                    )
                    for role in known_values
                )

        # Amendment §13 step 4 / CDD-049 §16.2: outcome derived from
        # combined observations.
        if observations:
            # Missingness (independent of canonicalization) or a genuine
            # value conflict -- either way, a real evaluation row is
            # inserted.
            outcome = EvaluationOutcome.VIOLATED
        elif canonicalization_failed:
            # CDD-049 §16.2: no missingness, canonicalization failed for a
            # known participant, no successful comparison was possible --
            # the ENTIRE attempt is NOT_EVALUABLE. Zero new
            # QualityComparisonEvaluation row, never a fabricated
            # CROSS_SOURCE_VALUE_CONFLICT.
            return None
        elif len(known_values) >= 2:
            outcome = EvaluationOutcome.SATISFIED
        else:
            # CDD-040 §30: a single observed value, with no
            # deterministically-provable missingness either, cannot prove
            # or disprove cross-source consistency.
            return None

        return outcome, tuple(observations), tuple(participants), tuple(canonical_projections)


def _assert_rule_and_correspondence_scope(
    *, rule: QualityRule, correspondence: ComparisonSubjectCorrespondence
) -> None:
    if rule.dimension is not QualityDimension.CONSISTENCY:
        raise ValidationException("rule.dimension must be CONSISTENCY for cross-source evaluation")
    if "participants" not in rule.rule_parameters:
        raise ValidationException("rule.rule_parameters must contain 'participants'")
