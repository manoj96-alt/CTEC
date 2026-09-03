"""Repository for OQI5-I1 -- Deterministic Remediation Foundation
(CDD-043 §11-§17; Artifact Authorization §2 row 6). Persists
`RemediationCase`/`RemediationCandidate`/`RemediationInstruction`/
`RemediationAuthorization`, and reads (never writes) the existing
OQI1/OQI2/OQI3 finding and evidence tables needed to extract candidates
and to refresh a case's status from a Finding's own current state.

`get_authorization_for_update` performs a `SELECT ... FOR UPDATE` on the
target authorization row -- the same row-level lock technique Gate S's own
`GateSApprovalRepositoryImpl.get_for_update` uses (CDD-036 §20) -- so
OQI5's independent authorization object gets the identical one-time-
consumption guarantee without touching Gate S's table.

`OqiRemediationParticipantReader` assembles `ParticipantObservation`
inputs for `extract_oqi2_candidates` by reading
`quality_comparison_evaluation_participants`,
`quality_comparison_evaluation_evidence`, and
`quality_comparison_evaluation_observations` directly -- no existing OQI2
repository method reconstructs a full evaluation's participant/evidence/
observation set, so this is new read-only query logic, mirroring
`OqiBusinessRuleEvidenceValueReader`'s own precedent for resolving
evidence content in a separate statement after the primary read (safe
because `field_value_evidence` is insert-only)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.oqi_cross_source.evaluation import ComparisonObservationType
from app.domain.oqi_remediation.authorization import (
    RemediationActionType,
    RemediationAuthorization,
    RemediationAuthorizationStatus,
    RemediationInstruction,
)
from app.domain.oqi_remediation.candidate import (
    ParticipantObservation,
    RemediationCandidate,
    RemediationCandidateBasis,
)
from app.domain.oqi_remediation.case import FindingFamily, RemediationCase, RemediationCaseStatus
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_canonical_standard import (
    CanonicalStandardValueORM,
    QualityEvaluationCanonicalStandardORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_evaluation import (
    QualityComparisonEvaluationEvidenceORM,
    QualityComparisonEvaluationObservationORM,
    QualityComparisonEvaluationParticipantORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_quality_evaluation import (
    QualityEvaluationEvidenceORM,
    QualityEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_reference_evidence import (
    QualityEvaluationReferenceEvidenceORM,
    ReferenceEvidenceAssertionORM,
)
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
    OqiRemediationCandidateORM,
    OqiRemediationCaseORM,
    OqiRemediationInstructionORM,
)


@dataclass(frozen=True, slots=True)
class FindingState:
    """Read-only projection of an OQI1/OQI2/OQI3 Finding's current-state
    fields relevant to remediation: whether it is resolved, and its
    `state_revision` for staleness binding (CDD-043 §15)."""

    status: str
    state_revision: int
    latest_evaluation_id: UUID | None


@dataclass(frozen=True, slots=True)
class AccuracyCandidateSupport:
    """CDD-048 §24: the exact data `extract_accuracy_candidates` needs,
    resolved read-only from what the Accuracy evaluator already persisted."""

    target_source_object_id: UUID
    target_source_field_id: UUID
    observed_evidence_id: UUID
    reference_value: str
    backing_assertion_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ConformityCandidateSupport:
    """CDD-049 §24: the exact data `extract_conformity_candidates` needs,
    resolved read-only from what the Conformity evaluator already
    persisted."""

    target_source_object_id: UUID
    target_source_field_id: UUID
    observed_evidence_id: UUID
    canonical_value: str
    canonical_value_id: UUID


class OqiRemediationRepository(Protocol):
    def get_case(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> RemediationCase | None: ...

    def get_case_by_id(self, case_id: UUID) -> RemediationCase | None: ...

    def save_case(self, case: RemediationCase) -> None: ...

    def save_candidates_idempotent(self, candidates: tuple[RemediationCandidate, ...]) -> None: ...

    def get_candidates_for_case(self, case_id: UUID) -> tuple[RemediationCandidate, ...]: ...

    def get_candidate(self, candidate_id: UUID) -> RemediationCandidate | None: ...

    def save_instruction(self, instruction: RemediationInstruction) -> None: ...

    def get_instruction(self, instruction_id: UUID) -> RemediationInstruction | None: ...

    def create_authorization(self, authorization: RemediationAuthorization) -> None: ...

    def get_authorization_by_id(
        self, authorization_id: UUID
    ) -> RemediationAuthorization | None: ...

    def get_authorization_for_update(
        self, authorization_id: UUID
    ) -> RemediationAuthorization | None: ...

    def update_authorization_decision(self, authorization: RemediationAuthorization) -> None: ...

    def consume_authorization(
        self, *, authorization_id: UUID, execution_id: UUID, now: datetime
    ) -> None: ...

    def get_oqi1_finding_state(
        self, *, tenant_id: str, finding_id: UUID
    ) -> FindingState | None: ...

    def get_oqi2_finding_state(
        self, *, tenant_id: str, finding_id: UUID
    ) -> FindingState | None: ...

    def get_oqi3_finding_state(
        self, *, tenant_id: str, finding_id: UUID
    ) -> FindingState | None: ...


class OqiRemediationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_case(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> RemediationCase | None:
        model = self.session.execute(
            select(OqiRemediationCaseORM).where(
                OqiRemediationCaseORM.tenant_id == tenant_id,
                OqiRemediationCaseORM.finding_family == finding_family.value,
                OqiRemediationCaseORM.finding_id == finding_id,
            )
        ).scalar_one_or_none()
        return None if model is None else _case_to_domain(model)

    def get_case_by_id(self, case_id: UUID) -> RemediationCase | None:
        model = self.session.get(OqiRemediationCaseORM, case_id)
        return None if model is None else _case_to_domain(model)

    def save_case(self, case: RemediationCase) -> None:
        model = self.session.get(OqiRemediationCaseORM, case.case_id)
        if model is None:
            self.session.add(_case_to_orm(case))
            return
        model.status = case.status.value
        model.external_execution_claimed = case.external_execution_claimed
        model.external_execution_claimed_on = case.external_execution_claimed_on
        model.updated_on = case.updated_on

    def save_candidates_idempotent(self, candidates: tuple[RemediationCandidate, ...]) -> None:
        """CDD-043 §12: candidates are immutable and deterministically
        identified, so re-extracting the same evidence set is a no-op --
        mirroring `insert_evaluation_idempotent`'s check-then-insert
        technique rather than a database-level upsert."""
        for candidate in candidates:
            if self.session.get(OqiRemediationCandidateORM, candidate.candidate_id) is not None:
                continue
            self.session.add(_candidate_to_orm(candidate))

    def get_candidates_for_case(self, case_id: UUID) -> tuple[RemediationCandidate, ...]:
        models = (
            self.session.execute(
                select(OqiRemediationCandidateORM)
                .where(OqiRemediationCandidateORM.case_id == case_id)
                .order_by(OqiRemediationCandidateORM.candidate_id)
            )
            .scalars()
            .all()
        )
        return tuple(_candidate_to_domain(model) for model in models)

    def get_candidate(self, candidate_id: UUID) -> RemediationCandidate | None:
        model = self.session.get(OqiRemediationCandidateORM, candidate_id)
        return None if model is None else _candidate_to_domain(model)

    def save_instruction(self, instruction: RemediationInstruction) -> None:
        if self.session.get(OqiRemediationInstructionORM, instruction.instruction_id) is not None:
            return
        self.session.add(_instruction_to_orm(instruction))

    def get_instruction(self, instruction_id: UUID) -> RemediationInstruction | None:
        model = self.session.get(OqiRemediationInstructionORM, instruction_id)
        return None if model is None else _instruction_to_domain(model)

    def create_authorization(self, authorization: RemediationAuthorization) -> None:
        self.session.add(_authorization_to_orm(authorization))

    def get_authorization_by_id(self, authorization_id: UUID) -> RemediationAuthorization | None:
        model = self.session.get(OqiRemediationAuthorizationORM, authorization_id)
        return None if model is None else _authorization_to_domain(model)

    def get_authorization_for_update(
        self, authorization_id: UUID
    ) -> RemediationAuthorization | None:
        model = self.session.execute(
            select(OqiRemediationAuthorizationORM)
            .where(OqiRemediationAuthorizationORM.authorization_id == authorization_id)
            .with_for_update()
        ).scalar_one_or_none()
        return None if model is None else _authorization_to_domain(model)

    def update_authorization_decision(self, authorization: RemediationAuthorization) -> None:
        model = self.session.get(OqiRemediationAuthorizationORM, authorization.authorization_id)
        assert model is not None
        model.status = authorization.status.value
        model.decided_by = authorization.decided_by
        model.decided_on = authorization.decided_on
        model.rejection_reason = authorization.rejection_reason

    def consume_authorization(
        self, *, authorization_id: UUID, execution_id: UUID, now: datetime
    ) -> None:
        model = self.session.get(OqiRemediationAuthorizationORM, authorization_id)
        assert model is not None
        model.consumed_on = now
        model.consumed_execution_id = execution_id

    def get_oqi1_finding_state(self, *, tenant_id: str, finding_id: UUID) -> FindingState | None:
        model = self.session.get(QualityFindingORM, finding_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        return FindingState(
            status=model.status, state_revision=model.state_revision, latest_evaluation_id=None
        )

    def get_oqi2_finding_state(self, *, tenant_id: str, finding_id: UUID) -> FindingState | None:
        model = self.session.get(QualityComparisonFindingORM, finding_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        return FindingState(
            status=model.status,
            state_revision=model.state_revision,
            latest_evaluation_id=model.latest_evaluation_id,
        )

    def get_oqi3_finding_state(self, *, tenant_id: str, finding_id: UUID) -> FindingState | None:
        model = self.session.get(BusinessRuleFindingORM, finding_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        return FindingState(
            status=model.status, state_revision=model.state_revision, latest_evaluation_id=None
        )

    def get_accuracy_candidate_support(
        self, *, tenant_id: str, finding_id: UUID
    ) -> AccuracyCandidateSupport | None:
        """CDD-048 §24 (OQI-H2-I-R1 narrow Artifact Authorization
        correction, disclosed in the OQI-H2-I final report): resolves the
        exact data `extract_accuracy_candidates` needs -- the observed
        evidence that produced this REFERENCE_VALUE_UNSUPPORTED Finding's
        latest VIOLATED evaluation, and the Reference Evidence that
        evaluation consulted. Never re-derives the comparison; only reads
        what the Accuracy evaluator itself already persisted. Intentionally
        NOT declared on `OqiRemediationRepository`'s Protocol -- mirrors
        `has_qualifying_coverage_for_dimension`'s own precedent for a
        narrow, additive, read-only capability."""
        finding_model = self.session.get(QualityFindingORM, finding_id)
        if finding_model is None or finding_model.tenant_id != tenant_id:
            return None
        evaluation_model = (
            self.session.query(QualityEvaluationORM)
            .filter(
                QualityEvaluationORM.tenant_id == tenant_id,
                QualityEvaluationORM.quality_condition_id == finding_model.quality_condition_id,
                QualityEvaluationORM.source_object_id == finding_model.source_object_id,
                QualityEvaluationORM.source_record_reference
                == finding_model.source_record_reference,
                QualityEvaluationORM.source_field_id == finding_model.source_field_id,
                QualityEvaluationORM.outcome == "VIOLATED",
            )
            .order_by(QualityEvaluationORM.evaluated_on.desc())
            .first()
        )
        if evaluation_model is None:
            return None
        evidence_row = (
            self.session.query(QualityEvaluationEvidenceORM)
            .filter(QualityEvaluationEvidenceORM.evaluation_id == evaluation_model.evaluation_id)
            .order_by(QualityEvaluationEvidenceORM.sequence_index.asc())
            .first()
        )
        if evidence_row is None:
            return None
        link_rows = (
            self.session.query(QualityEvaluationReferenceEvidenceORM)
            .filter(
                QualityEvaluationReferenceEvidenceORM.evaluation_id
                == evaluation_model.evaluation_id
            )
            .all()
        )
        if not link_rows:
            return None
        assertion_ids = tuple(row.assertion_id for row in link_rows)
        first_assertion = self.session.get(ReferenceEvidenceAssertionORM, assertion_ids[0])
        if first_assertion is None:
            return None
        return AccuracyCandidateSupport(
            target_source_object_id=finding_model.source_object_id,
            target_source_field_id=finding_model.source_field_id,
            observed_evidence_id=evidence_row.field_value_evidence_id,
            reference_value=first_assertion.asserted_value,
            backing_assertion_ids=assertion_ids,
        )

    def get_conformity_candidate_support(
        self, *, tenant_id: str, finding_id: UUID
    ) -> ConformityCandidateSupport | None:
        """CDD-049 §24: resolves the exact data `extract_conformity_
        candidates` needs -- the observed evidence that produced this
        NON_CANONICAL_REPRESENTATION Finding's latest VIOLATED evaluation,
        and the CanonicalStandard value that evaluation consulted. Never
        re-derives the comparison; only reads what the Conformity evaluator
        itself already persisted. Intentionally NOT declared on
        `OqiRemediationRepository`'s Protocol -- mirrors `get_accuracy_
        candidate_support`'s own precedent exactly."""
        finding_model = self.session.get(QualityFindingORM, finding_id)
        if finding_model is None or finding_model.tenant_id != tenant_id:
            return None
        evaluation_model = (
            self.session.query(QualityEvaluationORM)
            .filter(
                QualityEvaluationORM.tenant_id == tenant_id,
                QualityEvaluationORM.quality_condition_id == finding_model.quality_condition_id,
                QualityEvaluationORM.source_object_id == finding_model.source_object_id,
                QualityEvaluationORM.source_record_reference
                == finding_model.source_record_reference,
                QualityEvaluationORM.source_field_id == finding_model.source_field_id,
                QualityEvaluationORM.outcome == "VIOLATED",
            )
            .order_by(QualityEvaluationORM.evaluated_on.desc())
            .first()
        )
        if evaluation_model is None:
            return None
        evidence_row = (
            self.session.query(QualityEvaluationEvidenceORM)
            .filter(QualityEvaluationEvidenceORM.evaluation_id == evaluation_model.evaluation_id)
            .order_by(QualityEvaluationEvidenceORM.sequence_index.asc())
            .first()
        )
        if evidence_row is None:
            return None
        link_row = (
            self.session.query(QualityEvaluationCanonicalStandardORM)
            .filter(
                QualityEvaluationCanonicalStandardORM.evaluation_id
                == evaluation_model.evaluation_id
            )
            .first()
        )
        if link_row is None:
            return None
        canonical_value = self.session.get(CanonicalStandardValueORM, link_row.canonical_value_id)
        if canonical_value is None:
            return None
        return ConformityCandidateSupport(
            target_source_object_id=finding_model.source_object_id,
            target_source_field_id=finding_model.source_field_id,
            observed_evidence_id=evidence_row.field_value_evidence_id,
            canonical_value=canonical_value.canonical_representation,
            canonical_value_id=canonical_value.canonical_value_id,
        )


class OqiRemediationParticipantReader:
    """Read-only assembly of `ParticipantObservation` inputs to
    `extract_oqi2_candidates`, from OQI2's own persisted evaluation
    tables. Never writes to any OQI2 table."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def load_participant_observations(
        self, evaluation_id: UUID
    ) -> tuple[ParticipantObservation, ...]:
        participants = (
            self.session.execute(
                select(QualityComparisonEvaluationParticipantORM).where(
                    QualityComparisonEvaluationParticipantORM.evaluation_id == evaluation_id
                )
            )
            .scalars()
            .all()
        )
        evidence_rows = (
            self.session.execute(
                select(QualityComparisonEvaluationEvidenceORM)
                .where(QualityComparisonEvaluationEvidenceORM.evaluation_id == evaluation_id)
                .order_by(
                    QualityComparisonEvaluationEvidenceORM.participant_role,
                    QualityComparisonEvaluationEvidenceORM.sequence_index,
                )
            )
            .scalars()
            .all()
        )
        observation_rows = (
            self.session.execute(
                select(QualityComparisonEvaluationObservationORM).where(
                    QualityComparisonEvaluationObservationORM.evaluation_id == evaluation_id
                )
            )
            .scalars()
            .all()
        )

        primary_evidence_by_role: dict[str, UUID] = {}
        for row in evidence_rows:
            primary_evidence_by_role.setdefault(row.participant_role, row.field_value_evidence_id)

        observed_values = self._read_evidence_values(set(primary_evidence_by_role.values()))

        conflicting_roles = {
            row.participant_role
            for row in observation_rows
            if row.observation_type == ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT.value
        }
        missing_roles = {
            row.participant_role
            for row in observation_rows
            if row.observation_type
            == ComparisonObservationType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING.value
        }

        result = []
        for participant in participants:
            evidence_id = primary_evidence_by_role.get(participant.participant_role)
            observed_value = observed_values.get(evidence_id) if evidence_id else None
            result.append(
                ParticipantObservation(
                    role=participant.participant_role,
                    source_object_id=participant.source_object_id,
                    source_field_id=participant.source_field_id,
                    observed_value=observed_value,
                    evidence_id=evidence_id,
                    is_conflicting=participant.participant_role in conflicting_roles,
                    is_missing=participant.participant_role in missing_roles,
                    authoritative=participant.authoritative,
                )
            )
        return tuple(result)

    def _read_evidence_values(self, evidence_ids: set[UUID]) -> dict[UUID, str]:
        if not evidence_ids:
            return {}
        rows = self.session.execute(
            select(
                FieldValueEvidenceORM.field_value_evidence_id,
                FieldValueEvidenceORM.observed_representation,
            ).where(FieldValueEvidenceORM.field_value_evidence_id.in_(evidence_ids))
        ).all()
        return {row[0]: row[1] for row in rows}


def _case_to_orm(case: RemediationCase) -> OqiRemediationCaseORM:
    return OqiRemediationCaseORM(
        case_id=case.case_id,
        tenant_id=case.tenant_id,
        finding_family=case.finding_family.value,
        finding_id=case.finding_id,
        status=case.status.value,
        external_execution_claimed=case.external_execution_claimed,
        external_execution_claimed_on=case.external_execution_claimed_on,
        created_on=case.created_on,
        updated_on=case.updated_on,
    )


def _case_to_domain(model: OqiRemediationCaseORM) -> RemediationCase:
    return RemediationCase(
        case_id=model.case_id,
        tenant_id=model.tenant_id,
        finding_family=FindingFamily(model.finding_family),
        finding_id=model.finding_id,
        status=RemediationCaseStatus(model.status),
        external_execution_claimed=model.external_execution_claimed,
        external_execution_claimed_on=model.external_execution_claimed_on,
        created_on=model.created_on,
        updated_on=model.updated_on,
    )


def _candidate_to_orm(candidate: RemediationCandidate) -> OqiRemediationCandidateORM:
    return OqiRemediationCandidateORM(
        candidate_id=candidate.candidate_id,
        case_id=candidate.case_id,
        target_source_object_id=candidate.target_source_object_id,
        target_source_field_id=candidate.target_source_field_id,
        proposed_value=candidate.proposed_value,
        supporting_evidence_ids=[str(e) for e in candidate.supporting_evidence_ids],
        conflicting_evidence_ids=[str(e) for e in candidate.conflicting_evidence_ids],
        missing_participant_roles=list(candidate.missing_participant_roles),
        authority_participant_role=candidate.authority_participant_role,
        basis=candidate.basis.value,
        extracted_at=candidate.extracted_at,
    )


def _candidate_to_domain(model: OqiRemediationCandidateORM) -> RemediationCandidate:
    return RemediationCandidate(
        candidate_id=model.candidate_id,
        case_id=model.case_id,
        target_source_object_id=model.target_source_object_id,
        target_source_field_id=model.target_source_field_id,
        proposed_value=model.proposed_value,
        supporting_evidence_ids=tuple(UUID(e) for e in model.supporting_evidence_ids),
        conflicting_evidence_ids=tuple(UUID(e) for e in model.conflicting_evidence_ids),
        missing_participant_roles=tuple(model.missing_participant_roles),
        authority_participant_role=model.authority_participant_role,
        basis=RemediationCandidateBasis(model.basis),
        extracted_at=model.extracted_at,
    )


def _instruction_to_orm(instruction: RemediationInstruction) -> OqiRemediationInstructionORM:
    return OqiRemediationInstructionORM(
        instruction_id=instruction.instruction_id,
        tenant_id=instruction.tenant_id,
        finding_id=instruction.finding_id,
        finding_state_revision=instruction.finding_state_revision,
        case_id=instruction.case_id,
        candidate_id=instruction.candidate_id,
        target_source_object_id=instruction.target_source_object_id,
        target_source_field_id=instruction.target_source_field_id,
        action_type=instruction.action_type.value,
        payload_digest=instruction.payload_digest,
        agent_recommendation_id=instruction.agent_recommendation_id,
        created_by=instruction.created_by,
        created_on=instruction.created_on,
    )


def _instruction_to_domain(model: OqiRemediationInstructionORM) -> RemediationInstruction:
    return RemediationInstruction(
        instruction_id=model.instruction_id,
        tenant_id=model.tenant_id,
        finding_id=model.finding_id,
        finding_state_revision=model.finding_state_revision,
        case_id=model.case_id,
        candidate_id=model.candidate_id,
        target_source_object_id=model.target_source_object_id,
        target_source_field_id=model.target_source_field_id,
        action_type=RemediationActionType(model.action_type),
        payload_digest=model.payload_digest,
        agent_recommendation_id=model.agent_recommendation_id,
        created_by=model.created_by,
        created_on=model.created_on,
    )


def _authorization_to_orm(
    authorization: RemediationAuthorization,
) -> OqiRemediationAuthorizationORM:
    return OqiRemediationAuthorizationORM(
        authorization_id=authorization.authorization_id,
        tenant_id=authorization.tenant_id,
        instruction_id=authorization.instruction_id,
        payload_digest=authorization.payload_digest,
        requested_by=authorization.requested_by,
        requested_on=authorization.requested_on,
        status=authorization.status.value,
        decided_by=authorization.decided_by,
        decided_on=authorization.decided_on,
        rejection_reason=authorization.rejection_reason,
        consumed_on=authorization.consumed_on,
        consumed_execution_id=authorization.consumed_execution_id,
    )


def _authorization_to_domain(
    model: OqiRemediationAuthorizationORM,
) -> RemediationAuthorization:
    return RemediationAuthorization(
        authorization_id=model.authorization_id,
        tenant_id=model.tenant_id,
        instruction_id=model.instruction_id,
        payload_digest=model.payload_digest,
        requested_by=model.requested_by,
        requested_on=model.requested_on,
        status=RemediationAuthorizationStatus(model.status),
        decided_by=model.decided_by,
        decided_on=model.decided_on,
        rejection_reason=model.rejection_reason,
        consumed_on=model.consumed_on,
        consumed_execution_id=model.consumed_execution_id,
    )
