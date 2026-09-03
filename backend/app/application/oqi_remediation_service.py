"""OQI5-I1 -- Deterministic Remediation Foundation application service
(CDD-043 §11-§17; Artifact Authorization §2 row 7). Orchestrates
candidate extraction, instruction construction, and the
`RemediationAuthorization` lifecycle -- mirroring `GateSApprovalService`'s
exact request/decide/execute structure and fail-closed diagnostic-code
discipline (CDD-043 §9), but against OQI5's own structurally independent
authorization object, never Gate S's.

Zero new evaluation logic is introduced here (CDD-043 §17): `refresh_case`
only *reads* an OQI1/OQI2/OQI3 Finding's own current `status`/
`state_revision` (all three families reuse `QualityFindingStatus`
directly) and reflects it onto the case -- it never decides whether a
Finding is resolved, and `report_external_execution` never itself
resolves a Finding or sets a case to `RESOLVED`; only `refresh_case`,
called after some independent, later, existing OQI evaluator re-run, can
do that."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.oqi_remediation.authorization import (
    RemediationActionType,
    RemediationAuthorization,
    RemediationAuthorizationStatus,
    RemediationInstruction,
    compute_payload_digest,
)
from app.domain.oqi_remediation.candidate import (
    RemediationCandidate,
    extract_accuracy_candidates,
    extract_conformity_candidates,
    extract_oqi1_candidates,
    extract_oqi2_candidates,
    extract_oqi3_candidates,
    extract_reasonableness_candidates,
)
from app.domain.oqi_remediation.case import (
    FindingFamily,
    RemediationCase,
    RemediationCaseStatus,
    derive_remediation_case_id,
    open_or_reuse_case,
    record_external_execution_claim,
    refresh_case_status_from_finding,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    FindingState,
    OqiRemediationParticipantReader,
    OqiRemediationRepository,
)

_RESOLVED_STATUS = "RESOLVED"


class OqiRemediationError(Exception):
    """Carries one of this module's closed diagnostic codes (mirroring
    `GateSApprovalError`'s shape) -- no raw internal exception escapes."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class OqiRemediationService:
    def __init__(
        self,
        *,
        repository: OqiRemediationRepository,
        participant_reader: OqiRemediationParticipantReader,
    ) -> None:
        self._repository = repository
        self._participant_reader = participant_reader

    def extract_candidates(
        self,
        *,
        tenant_id: str,
        finding_family: FindingFamily,
        finding_id: UUID,
        quality_dimension: str | None = None,
        now: datetime | None = None,
    ) -> tuple[RemediationCase, tuple[RemediationCandidate, ...]]:
        """CDD-048 §24 (OQI-H2-I-R1 narrow Artifact Authorization
        correction, disclosed in the OQI-H2-I final report):
        `quality_dimension` is a new, optional, backward-compatible
        parameter -- every existing call site (which never passes it)
        continues to dispatch exactly as before, purely on
        `finding_family`. ACCURACY/REASONABLENESS Findings share OQI1's/
        OQI3's own `finding_family` values (CDD-048 §12 -- no new
        `FindingFamily` member exists), so they MUST be distinguished by
        `quality_dimension` here, never by `finding_family` alone -- this
        is the one dispatch site CDD-048 §12.3 identifies as requiring the
        new semantic axis, not just the existing physical-storage one."""
        moment = now if now is not None else datetime.now(UTC)
        finding_state = self._get_finding_state(
            finding_family=finding_family, tenant_id=tenant_id, finding_id=finding_id
        )
        if finding_state is None:
            raise OqiRemediationError("REMEDIATION_FINDING_NOT_FOUND")

        existing_case = self._repository.get_case(
            tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
        )

        if quality_dimension == "ACCURACY":
            case_id = derive_remediation_case_id(
                tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
            )
            candidates: tuple[RemediationCandidate, ...] = self._extract_accuracy_candidates(
                tenant_id=tenant_id, finding_id=finding_id, case_id=case_id, moment=moment
            )
        elif quality_dimension == "CONFORMITY":
            case_id = derive_remediation_case_id(
                tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
            )
            candidates = self._extract_conformity_candidates(
                tenant_id=tenant_id, finding_id=finding_id, case_id=case_id, moment=moment
            )
        elif quality_dimension == "REASONABLENESS":
            candidates = extract_reasonableness_candidates()
        elif finding_family is FindingFamily.OQI1:
            candidates = extract_oqi1_candidates()
        elif finding_family is FindingFamily.OQI3:
            candidates = extract_oqi3_candidates()
        else:
            candidates = self._extract_oqi2_candidates(
                tenant_id=tenant_id,
                finding_id=finding_id,
                finding_family=finding_family,
                latest_evaluation_id=finding_state.latest_evaluation_id,
                existing_case=existing_case,
                moment=moment,
            )

        status = (
            RemediationCaseStatus.CANDIDATE_READY
            if candidates
            else RemediationCaseStatus.STEWARD_INVESTIGATION
        )
        case = open_or_reuse_case(
            existing=existing_case,
            tenant_id=tenant_id,
            finding_family=finding_family,
            finding_id=finding_id,
            status=status,
            now=moment,
        )
        self._repository.save_case(case)
        self._repository.save_candidates_idempotent(candidates)
        return case, candidates

    def _extract_oqi2_candidates(
        self,
        *,
        tenant_id: str,
        finding_id: UUID,
        finding_family: FindingFamily,
        latest_evaluation_id: UUID | None,
        existing_case: RemediationCase | None,
        moment: datetime,
    ) -> tuple[RemediationCandidate, ...]:
        if latest_evaluation_id is None:
            return ()
        case_id = (
            existing_case.case_id
            if existing_case is not None
            else self._provisional_case_id(
                tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
            )
        )
        participants = self._participant_reader.load_participant_observations(latest_evaluation_id)
        remediable = [p for p in participants if p.is_conflicting or p.is_missing]
        candidates: list[RemediationCandidate] = []
        for target in remediable:
            others = [p for p in participants if p.role != target.role]
            candidates.extend(
                extract_oqi2_candidates(
                    case_id=case_id,
                    target_source_object_id=target.source_object_id,
                    target_source_field_id=target.source_field_id,
                    participants=others,
                    now=moment,
                )
            )
        return tuple(candidates)

    def _extract_accuracy_candidates(
        self, *, tenant_id: str, finding_id: UUID, case_id: UUID, moment: datetime
    ) -> tuple[RemediationCandidate, ...]:
        """CDD-048 §24: `get_accuracy_candidate_support` is intentionally
        NOT part of `OqiRemediationRepository`'s Protocol (mirrors the
        established `has_qualifying_coverage_for_dimension` precedent) --
        accessed defensively so a repository/fake that predates this
        capability degrades to zero candidates (STEWARD_INVESTIGATION)
        rather than raising."""
        getter = getattr(self._repository, "get_accuracy_candidate_support", None)
        if getter is None:
            return ()
        support = getter(tenant_id=tenant_id, finding_id=finding_id)
        if support is None:
            return ()
        return extract_accuracy_candidates(
            case_id=case_id,
            target_source_object_id=support.target_source_object_id,
            target_source_field_id=support.target_source_field_id,
            observed_evidence_id=support.observed_evidence_id,
            reference_value=support.reference_value,
            backing_assertion_ids=support.backing_assertion_ids,
            now=moment,
        )

    def _extract_conformity_candidates(
        self, *, tenant_id: str, finding_id: UUID, case_id: UUID, moment: datetime
    ) -> tuple[RemediationCandidate, ...]:
        """CDD-049 §24: `get_conformity_candidate_support` is intentionally
        NOT part of `OqiRemediationRepository`'s Protocol, mirroring
        `_extract_accuracy_candidates`'s identical precedent -- accessed
        defensively so a repository/fake that predates this capability
        degrades to zero candidates (STEWARD_INVESTIGATION) rather than
        raising."""
        getter = getattr(self._repository, "get_conformity_candidate_support", None)
        if getter is None:
            return ()
        support = getter(tenant_id=tenant_id, finding_id=finding_id)
        if support is None:
            return ()
        return extract_conformity_candidates(
            case_id=case_id,
            target_source_object_id=support.target_source_object_id,
            target_source_field_id=support.target_source_field_id,
            observed_evidence_id=support.observed_evidence_id,
            canonical_value=support.canonical_value,
            canonical_value_id=support.canonical_value_id,
            now=moment,
        )

    @staticmethod
    def _provisional_case_id(
        *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> UUID:
        return derive_remediation_case_id(
            tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
        )

    def construct_instruction(
        self,
        *,
        tenant_id: str,
        candidate_id: UUID,
        created_by: str,
        agent_recommendation_id: UUID | None = None,
        now: datetime | None = None,
    ) -> RemediationInstruction:
        moment = now if now is not None else datetime.now(UTC)
        candidate = self._repository.get_candidate(candidate_id)
        if candidate is None:
            raise OqiRemediationError("REMEDIATION_CANDIDATE_NOT_FOUND")
        case = self._get_case_by_id_or_raise(candidate.case_id)
        if case.tenant_id != tenant_id:
            raise OqiRemediationError("REMEDIATION_TENANT_MISMATCH")
        finding_state = self._get_finding_state(
            finding_family=case.finding_family, tenant_id=tenant_id, finding_id=case.finding_id
        )
        if finding_state is None:
            raise OqiRemediationError("REMEDIATION_FINDING_NOT_FOUND")

        action_type = RemediationActionType.UPDATE_FIELD
        digest = compute_payload_digest(
            tenant_id=tenant_id,
            finding_id=case.finding_id,
            finding_state_revision=finding_state.state_revision,
            case_id=case.case_id,
            candidate_id=candidate.candidate_id,
            target_source_object_id=candidate.target_source_object_id,
            target_source_field_id=candidate.target_source_field_id,
            action_type=action_type,
        )
        instruction = RemediationInstruction(
            instruction_id=uuid4(),
            tenant_id=tenant_id,
            finding_id=case.finding_id,
            finding_state_revision=finding_state.state_revision,
            case_id=case.case_id,
            candidate_id=candidate.candidate_id,
            target_source_object_id=candidate.target_source_object_id,
            target_source_field_id=candidate.target_source_field_id,
            action_type=action_type,
            payload_digest=digest,
            agent_recommendation_id=agent_recommendation_id,
            created_by=created_by,
            created_on=moment,
        )
        self._repository.save_instruction(instruction)
        updated_case = RemediationCase(
            case_id=case.case_id,
            tenant_id=case.tenant_id,
            finding_family=case.finding_family,
            finding_id=case.finding_id,
            status=RemediationCaseStatus.AWAITING_AUTHORITY,
            external_execution_claimed=case.external_execution_claimed,
            external_execution_claimed_on=case.external_execution_claimed_on,
            created_on=case.created_on,
            updated_on=moment,
        )
        self._repository.save_case(updated_case)
        return instruction

    def request_authorization(
        self,
        *,
        tenant_id: str,
        instruction_id: UUID,
        requested_by: str,
        now: datetime | None = None,
    ) -> RemediationAuthorization:
        moment = now if now is not None else datetime.now(UTC)
        instruction = self._repository.get_instruction(instruction_id)
        if instruction is None:
            raise OqiRemediationError("REMEDIATION_INSTRUCTION_NOT_FOUND")
        if instruction.tenant_id != tenant_id:
            raise OqiRemediationError("REMEDIATION_TENANT_MISMATCH")
        authorization = RemediationAuthorization(
            authorization_id=uuid4(),
            tenant_id=tenant_id,
            instruction_id=instruction_id,
            payload_digest=instruction.payload_digest,
            requested_by=requested_by,
            requested_on=moment,
            status=RemediationAuthorizationStatus.PENDING,
        )
        self._repository.create_authorization(authorization)
        return authorization

    def approve(
        self,
        *,
        tenant_id: str,
        authorization_id: UUID,
        decided_by: str,
        now: datetime | None = None,
    ) -> RemediationAuthorization:
        authorization = self._decide(
            tenant_id=tenant_id,
            authorization_id=authorization_id,
            decided_by=decided_by,
            new_status=RemediationAuthorizationStatus.APPROVED,
            rejection_reason=None,
            now=now,
        )
        instruction = self._repository.get_instruction(authorization.instruction_id)
        assert instruction is not None
        case = self._get_case_by_id_or_raise(instruction.case_id)
        moment = now if now is not None else datetime.now(UTC)
        self._repository.save_case(
            RemediationCase(
                case_id=case.case_id,
                tenant_id=case.tenant_id,
                finding_family=case.finding_family,
                finding_id=case.finding_id,
                status=RemediationCaseStatus.AUTHORIZED,
                external_execution_claimed=case.external_execution_claimed,
                external_execution_claimed_on=case.external_execution_claimed_on,
                created_on=case.created_on,
                updated_on=moment,
            )
        )
        return authorization

    def reject(
        self,
        *,
        tenant_id: str,
        authorization_id: UUID,
        decided_by: str,
        rejection_reason: str | None,
        now: datetime | None = None,
    ) -> RemediationAuthorization:
        return self._decide(
            tenant_id=tenant_id,
            authorization_id=authorization_id,
            decided_by=decided_by,
            new_status=RemediationAuthorizationStatus.REJECTED,
            rejection_reason=rejection_reason,
            now=now,
        )

    def _decide(
        self,
        *,
        tenant_id: str,
        authorization_id: UUID,
        decided_by: str,
        new_status: RemediationAuthorizationStatus,
        rejection_reason: str | None,
        now: datetime | None,
    ) -> RemediationAuthorization:
        moment = now if now is not None else datetime.now(UTC)
        authorization = self._repository.get_authorization_for_update(authorization_id)
        if authorization is None:
            raise OqiRemediationError("REMEDIATION_AUTHORIZATION_NOT_FOUND")
        if authorization.tenant_id != tenant_id:
            raise OqiRemediationError("REMEDIATION_TENANT_MISMATCH")
        if decided_by == authorization.requested_by:
            raise OqiRemediationError("REMEDIATION_SELF_APPROVAL_PROHIBITED")
        if authorization.status is not RemediationAuthorizationStatus.PENDING:
            raise OqiRemediationError("REMEDIATION_AUTHORIZATION_NOT_PENDING")

        decided = RemediationAuthorization(
            authorization_id=authorization.authorization_id,
            tenant_id=authorization.tenant_id,
            instruction_id=authorization.instruction_id,
            payload_digest=authorization.payload_digest,
            requested_by=authorization.requested_by,
            requested_on=authorization.requested_on,
            status=new_status,
            decided_by=decided_by,
            decided_on=moment,
            rejection_reason=rejection_reason,
            consumed_on=authorization.consumed_on,
            consumed_execution_id=authorization.consumed_execution_id,
        )
        self._repository.update_authorization_decision(decided)
        return decided

    def report_external_execution(
        self,
        *,
        tenant_id: str,
        authorization_id: UUID,
        now: datetime | None = None,
    ) -> RemediationCase:
        """CDD-043 §14-§16: the sole write path for an external/manual
        execution claim. Recomputes the payload digest from the
        instruction's *current* referenced candidate and the Finding's
        *current* `state_revision` -- read fresh, under the same row lock
        as consumption -- so any Finding-revision change, or any
        candidate/instruction drift, since authorization fails closed with
        `REMEDIATION_ACTION_MISMATCH` (the staleness contract, §15) with
        zero additional machinery. Consuming the authorization and
        recording the case's external-execution claim happen in the same
        call, exactly as Gate S's own `execute()` atomically writes its
        note and consumes its approval together."""
        moment = now if now is not None else datetime.now(UTC)
        authorization = self._repository.get_authorization_for_update(authorization_id)
        if authorization is None:
            raise OqiRemediationError("REMEDIATION_AUTHORIZATION_NOT_FOUND")
        if authorization.tenant_id != tenant_id:
            raise OqiRemediationError("REMEDIATION_TENANT_MISMATCH")
        if authorization.status is RemediationAuthorizationStatus.REJECTED:
            raise OqiRemediationError("REMEDIATION_AUTHORIZATION_REJECTED")
        if authorization.status is not RemediationAuthorizationStatus.APPROVED:
            raise OqiRemediationError("REMEDIATION_AUTHORIZATION_NOT_PENDING")
        if authorization.consumed_on is not None:
            raise OqiRemediationError("REMEDIATION_AUTHORIZATION_ALREADY_CONSUMED")

        instruction = self._repository.get_instruction(authorization.instruction_id)
        assert instruction is not None
        candidate = self._repository.get_candidate(instruction.candidate_id)
        if candidate is None:
            raise OqiRemediationError("REMEDIATION_CANDIDATE_NOT_FOUND")
        case = self._get_case_by_id_or_raise(instruction.case_id)
        finding_state = self._get_finding_state(
            finding_family=case.finding_family,
            tenant_id=tenant_id,
            finding_id=instruction.finding_id,
        )
        if finding_state is None:
            raise OqiRemediationError("REMEDIATION_FINDING_NOT_FOUND")
        recomputed_digest = compute_payload_digest(
            tenant_id=tenant_id,
            finding_id=instruction.finding_id,
            finding_state_revision=finding_state.state_revision,
            case_id=instruction.case_id,
            candidate_id=candidate.candidate_id,
            target_source_object_id=candidate.target_source_object_id,
            target_source_field_id=candidate.target_source_field_id,
            action_type=instruction.action_type,
        )
        if recomputed_digest != authorization.payload_digest:
            raise OqiRemediationError("REMEDIATION_ACTION_MISMATCH")

        execution_id = uuid4()
        self._repository.consume_authorization(
            authorization_id=authorization_id, execution_id=execution_id, now=moment
        )
        updated_case = record_external_execution_claim(case=case, now=moment)
        self._repository.save_case(updated_case)
        return updated_case

    def refresh_case(
        self,
        *,
        tenant_id: str,
        finding_family: FindingFamily,
        finding_id: UUID,
        now: datetime | None = None,
    ) -> RemediationCase:
        """CDD-043 §17: reflects the Finding's own, already-authoritative
        current `status` (set exclusively by the existing, unmodified
        OQI1/OQI2/OQI3 evaluator) onto the case. Introduces no new
        evaluation logic -- it is a read of a fact that already exists,
        never a decision."""
        moment = now if now is not None else datetime.now(UTC)
        case = self._repository.get_case(
            tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
        )
        if case is None:
            raise OqiRemediationError("REMEDIATION_CASE_NOT_FOUND")
        finding_state = self._get_finding_state(
            finding_family=finding_family, tenant_id=tenant_id, finding_id=finding_id
        )
        if finding_state is None:
            raise OqiRemediationError("REMEDIATION_FINDING_NOT_FOUND")
        updated_case = refresh_case_status_from_finding(
            case=case,
            finding_status_is_resolved=finding_state.status == _RESOLVED_STATUS,
            now=moment,
        )
        self._repository.save_case(updated_case)
        return updated_case

    def _get_finding_state(
        self, *, finding_family: FindingFamily, tenant_id: str, finding_id: UUID
    ) -> FindingState | None:
        if finding_family is FindingFamily.OQI1:
            return self._repository.get_oqi1_finding_state(
                tenant_id=tenant_id, finding_id=finding_id
            )
        if finding_family is FindingFamily.OQI2:
            return self._repository.get_oqi2_finding_state(
                tenant_id=tenant_id, finding_id=finding_id
            )
        return self._repository.get_oqi3_finding_state(tenant_id=tenant_id, finding_id=finding_id)

    def _get_case_by_id_or_raise(self, case_id: UUID) -> RemediationCase:
        case = self._repository.get_case_by_id(case_id)
        if case is None:
            raise OqiRemediationError("REMEDIATION_CASE_NOT_FOUND")
        return case
