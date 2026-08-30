"""OQI5-I2 -- Governed Real Agent Reasoning application service (CDD-043
§18-§24; Artifact Authorization §3 row 8). Orchestrates the frozen M2
topology: two genuinely parallel specialist `AgentRun`s against an
identical deterministic `AgentEvidencePacket`, deterministic code-only
aggregation preserving disagreement, one Recommendation Synthesizer
`AgentRun` consuming only the validated aggregate, and deterministic
validation of every model output before anything becomes an
`AgentAssessment`/`AgentRecommendation`.

No I2 code ever mutates a Finding's status, ever creates a
`RemediationAuthorization`, and ever performs a source write (CDD-043
§8/§14, phase §7-§9, §57-§59) -- this module contains none of that
capability at all, by construction: it has no import of, or dependency
on, any authorization-decision or source-write code path. A validated
`AgentRecommendation`'s `recommendation_id` is handed back to the caller
so it may be passed, purely as provenance, into I1's own, unmodified
`OqiRemediationService.construct_instruction(agent_recommendation_id=...)`
-- this module never constructs a `RemediationInstruction` itself."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.domain.oqi_remediation.case import FindingFamily, RemediationCase
from app.domain.oqi_remediation_agent.recommendation import (
    AgentAssessment,
    AgentRecommendation,
    AgentRecommendationValidator,
)
from app.domain.oqi_remediation_agent.role import AgentRole, AgentRoleId, build_role_v1
from app.domain.oqi_remediation_agent.run import (
    AgentEvidencePacket,
    AgentRun,
    AgentRunResultState,
    compute_evidence_packet_digest,
)
from app.infrastructure.model_provider.provider import ModelInvocationRequest, ModelProvider
from app.infrastructure.persistence.oqi_remediation_agent_repository import (
    OqiRemediationAgentPacketReader,
    OqiRemediationAgentRepository,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    FindingState,
    OqiRemediationRepository,
)

_SPECIALIST_ROLE_IDS: tuple[AgentRoleId, ...] = (
    AgentRoleId.EVIDENCE_CONSISTENCY_ANALYST,
    AgentRoleId.IMPACT_CONTINUITY_ANALYST,
)


class OqiRemediationAgentError(Exception):
    """Carries one of this module's closed diagnostic codes (mirroring
    `OqiRemediationError`'s shape) -- no raw internal exception escapes."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class SpecialistOutcome:
    role_id: AgentRoleId
    run: AgentRun
    assessment: AgentAssessment | None


@dataclass(frozen=True, slots=True)
class DeterministicAggregate:
    """CDD-043 §20: "plain deterministic code (union of cited references,
    concatenation of structured assessments) -- never a third model
    call." Disagreement is preserved explicitly (`accepted_assessments`
    always carries every validated specialist output separately) --
    aggregation never collapses disagreement into a majority vote (phase
    §30/§33/§90)."""

    accepted_assessments: tuple[AgentAssessment, ...]
    all_supporting_evidence_ids: tuple[UUID, ...]
    all_conflicting_evidence_ids: tuple[UUID, ...]
    all_impact_evaluation_ids: tuple[UUID, ...]

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "specialist_assessments": [
                {
                    "role_id": a.role_id,
                    "recommendation_type": a.recommendation_type.value,
                    "candidate_id": str(a.candidate_id) if a.candidate_id else None,
                    "supporting_evidence_ids": sorted(str(e) for e in a.supporting_evidence_ids),
                    "conflicting_evidence_ids": sorted(str(e) for e in a.conflicting_evidence_ids),
                    "impact_evaluation_ids": sorted(str(e) for e in a.impact_evaluation_ids),
                    "rationale": a.rationale,
                }
                for a in sorted(self.accepted_assessments, key=lambda a: a.role_id)
            ]
        }


@dataclass(frozen=True, slots=True)
class ReasoningOutcome:
    case_id: UUID
    specialist_outcomes: tuple[SpecialistOutcome, ...]
    synthesizer_run: AgentRun
    recommendation: AgentRecommendation | None


def build_deterministic_aggregate(
    assessments: tuple[AgentAssessment, ...],
) -> DeterministicAggregate:
    supporting: set[UUID] = set()
    conflicting: set[UUID] = set()
    impacts: set[UUID] = set()
    for a in assessments:
        supporting.update(a.supporting_evidence_ids)
        conflicting.update(a.conflicting_evidence_ids)
        impacts.update(a.impact_evaluation_ids)
    return DeterministicAggregate(
        accepted_assessments=assessments,
        all_supporting_evidence_ids=tuple(sorted(supporting, key=str)),
        all_conflicting_evidence_ids=tuple(sorted(conflicting, key=str)),
        all_impact_evaluation_ids=tuple(sorted(impacts, key=str)),
    )


class OqiRemediationAgentService:
    def __init__(
        self,
        *,
        agent_repository: OqiRemediationAgentRepository,
        packet_reader: OqiRemediationAgentPacketReader,
        remediation_repository: OqiRemediationRepository,
        provider: ModelProvider,
    ) -> None:
        self._agent_repository = agent_repository
        self._packet_reader = packet_reader
        self._remediation_repository = remediation_repository
        self._provider = provider
        self._validator = AgentRecommendationValidator()

    def reason_about_case(
        self, *, tenant_id: str, case_id: UUID, now: datetime | None = None
    ) -> ReasoningOutcome:
        moment = now if now is not None else datetime.now(UTC)
        case = self._remediation_repository.get_case_by_id(case_id)
        if case is None:
            raise OqiRemediationAgentError("REMEDIATION_AGENT_CASE_NOT_FOUND")
        if case.tenant_id != tenant_id:
            raise OqiRemediationAgentError("REMEDIATION_AGENT_TENANT_MISMATCH")

        finding_state = self._get_finding_state(case)
        if finding_state is None:
            raise OqiRemediationAgentError("REMEDIATION_AGENT_FINDING_NOT_FOUND")

        candidates = self._remediation_repository.get_candidates_for_case(case_id)

        roles = {role_id: self._ensure_role(role_id, now=moment) for role_id in AgentRoleId}

        packet = self._packet_reader.build_packet(
            case=case,
            candidates=candidates,
            finding_state_revision=finding_state.state_revision,
            evaluation_id=finding_state.latest_evaluation_id,
            role_version=1,
        )

        specialist_outcomes = self._run_specialists_parallel(
            tenant_id=tenant_id, case=case, packet=packet, roles=roles, now=moment
        )
        accepted_assessments = tuple(
            o.assessment for o in specialist_outcomes if o.assessment is not None
        )
        aggregate = build_deterministic_aggregate(accepted_assessments)

        synthesizer_run, recommendation = self._run_synthesizer(
            tenant_id=tenant_id,
            case=case,
            packet=packet,
            role=roles[AgentRoleId.RECOMMENDATION_SYNTHESIZER],
            aggregate=aggregate,
            now=moment,
        )

        return ReasoningOutcome(
            case_id=case_id,
            specialist_outcomes=specialist_outcomes,
            synthesizer_run=synthesizer_run,
            recommendation=recommendation,
        )

    def _ensure_role(self, role_id: AgentRoleId, *, now: datetime) -> AgentRole:
        existing = self._agent_repository.get_active_role(role_id)
        if existing is not None:
            return existing
        role = build_role_v1(role_id, now=now)
        self._agent_repository.save_role_if_absent(role)
        return role

    def _run_specialists_parallel(
        self,
        *,
        tenant_id: str,
        case: RemediationCase,
        packet: AgentEvidencePacket,
        roles: dict[AgentRoleId, AgentRole],
        now: datetime,
    ) -> tuple[SpecialistOutcome, ...]:
        """Genuine parallel orchestration (CDD-043 §20/phase §26): both
        specialist invocations (provider call + parse + deterministic
        validation) are dispatched concurrently against the identical
        packet, each reasoning independently -- neither ever sees the
        other's output (phase §27/§32). Persistence is deliberately kept
        out of the worker threads and performed afterward, sequentially,
        on the calling thread: the shared SQLAlchemy `Session` behind
        `self._agent_repository` is not thread-safe, and having two
        threads call `session.add(...)` concurrently would be a
        genuine concurrency defect, not a performance nicety -- computing
        both outcomes in parallel and persisting them serially preserves
        both the concurrency property this phase requires and DB safety."""
        with ThreadPoolExecutor(max_workers=len(_SPECIALIST_ROLE_IDS)) as pool:
            futures = {
                role_id: pool.submit(
                    self._compute_specialist_outcome,
                    case=case,
                    packet=packet,
                    role=roles[role_id],
                    tenant_id=tenant_id,
                    now=now,
                )
                for role_id in _SPECIALIST_ROLE_IDS
            }
            outcomes = tuple(futures[role_id].result() for role_id in _SPECIALIST_ROLE_IDS)

        for outcome in outcomes:
            self._agent_repository.save_run(outcome.run)
            if outcome.assessment is not None:
                self._agent_repository.save_assessment(outcome.assessment)
        return outcomes

    def _compute_specialist_outcome(
        self,
        *,
        tenant_id: str,
        case: RemediationCase,
        packet: AgentEvidencePacket,
        role: AgentRole,
        now: datetime,
    ) -> SpecialistOutcome:
        """Pure computation -- provider invocation, JSON parsing, and
        deterministic validation only. Never touches the repository/
        session, so it is safe to run inside a worker thread."""
        provisional_run, parsed = self._invoke(
            tenant_id=tenant_id,
            case=case,
            packet=packet,
            role=role,
            input_payload=packet.to_canonical_dict(),
            now=now,
        )
        if provisional_run.result_state is not AgentRunResultState.SUCCEEDED:
            assert parsed is None
            return SpecialistOutcome(role_id=role.role_id, run=provisional_run, assessment=None)

        assert parsed is not None
        validation = self._validator.validate_specialist_output(
            parsed, run_id=provisional_run.run_id, role=role, packet=packet
        )
        if not validation.accepted:
            assert validation.rejection is not None
            final_run = _as_rejected(provisional_run, reason=validation.rejection.reason.value)
            return SpecialistOutcome(role_id=role.role_id, run=final_run, assessment=None)

        assert validation.assessment is not None
        return SpecialistOutcome(
            role_id=role.role_id, run=provisional_run, assessment=validation.assessment
        )

    def _run_synthesizer(
        self,
        *,
        tenant_id: str,
        case: RemediationCase,
        packet: AgentEvidencePacket,
        role: AgentRole,
        aggregate: DeterministicAggregate,
        now: datetime,
    ) -> tuple[AgentRun, AgentRecommendation | None]:
        input_payload = {
            "evidence_packet": packet.to_canonical_dict(),
            **aggregate.to_canonical_dict(),
        }
        provisional_run, parsed = self._invoke(
            tenant_id=tenant_id,
            case=case,
            packet=packet,
            role=role,
            input_payload=input_payload,
            now=now,
        )
        if provisional_run.result_state is not AgentRunResultState.SUCCEEDED:
            assert parsed is None
            self._agent_repository.save_run(provisional_run)
            return provisional_run, None

        assert parsed is not None
        validation = self._validator.validate_recommendation_output(
            parsed, role=role, packet=packet
        )
        if not validation.accepted:
            assert validation.rejection is not None
            final_run = _as_rejected(provisional_run, reason=validation.rejection.reason.value)
            self._agent_repository.save_run(final_run)
            return final_run, None

        fields = validation.recommendation_fields
        assert fields is not None
        self._agent_repository.save_run(provisional_run)
        recommendation = AgentRecommendation(
            recommendation_id=uuid4(),
            run_id=provisional_run.run_id,
            case_id=case.case_id,
            recommendation_type=fields.recommendation_type,
            candidate_id=fields.candidate_id,
            supporting_evidence_ids=fields.supporting_evidence_ids,
            conflicting_evidence_ids=fields.conflicting_evidence_ids,
            rationale=fields.rationale,
            created_on=now,
        )
        self._agent_repository.save_recommendation(recommendation)
        return provisional_run, recommendation

    def _invoke(
        self,
        *,
        tenant_id: str,
        case: RemediationCase,
        packet: AgentEvidencePacket,
        role: AgentRole,
        input_payload: dict[str, Any],
        now: datetime,
    ) -> tuple[AgentRun, object | None]:
        """Invokes the provider and returns a not-yet-persisted `AgentRun`
        plus the parsed JSON content (`None` if the run is not
        `SUCCEEDED`). The caller is solely responsible for persisting the
        run exactly once, after any content-level validation decides its
        true final `result_state` -- `save_run` is a no-op for an already
        -persisted `run_id` (idempotent-replay safety, CDD-043 §17
        precedent), so persisting a provisional `SUCCEEDED` row here and
        then trying to overwrite it with `REJECTED_OUTPUT` would silently
        fail to record the real outcome."""
        digest = compute_evidence_packet_digest(packet, role_version=role.version)
        result = self._provider.invoke(
            ModelInvocationRequest(
                role_id=role.role_id.value,
                role_version=role.version,
                system_instructions=role.instructions,
                input_payload=input_payload,
            )
        )
        run_id = uuid4()
        if not result.succeeded:
            assert result.failure_kind is not None
            run = AgentRun(
                run_id=run_id,
                tenant_id=tenant_id,
                case_id=case.case_id,
                role_id=role.role_id.value,
                role_version=role.version,
                provider=result.provider,
                model=result.model,
                evidence_packet_digest=digest,
                raw_output=None,
                result_state=AgentRunResultState.FAILED,
                failure_reason=result.failure_kind.value,
                created_on=now,
            )
            return run, None

        assert result.raw_text is not None
        try:
            parsed = json.loads(result.raw_text)
        except json.JSONDecodeError:
            run = AgentRun(
                run_id=run_id,
                tenant_id=tenant_id,
                case_id=case.case_id,
                role_id=role.role_id.value,
                role_version=role.version,
                provider=result.provider,
                model=result.model,
                evidence_packet_digest=digest,
                raw_output=None,
                result_state=AgentRunResultState.FAILED,
                failure_reason="MALFORMED_RESPONSE",
                created_on=now,
            )
            return run, None

        run = AgentRun(
            run_id=run_id,
            tenant_id=tenant_id,
            case_id=case.case_id,
            role_id=role.role_id.value,
            role_version=role.version,
            provider=result.provider,
            model=result.model,
            evidence_packet_digest=digest,
            raw_output=json.dumps(parsed, sort_keys=True, separators=(",", ":")),
            result_state=AgentRunResultState.SUCCEEDED,
            failure_reason=None,
            created_on=now,
        )
        return run, parsed

    def _get_finding_state(self, case: RemediationCase) -> FindingState | None:
        if case.finding_family is FindingFamily.OQI1:
            return self._remediation_repository.get_oqi1_finding_state(
                tenant_id=case.tenant_id, finding_id=case.finding_id
            )
        if case.finding_family is FindingFamily.OQI2:
            return self._remediation_repository.get_oqi2_finding_state(
                tenant_id=case.tenant_id, finding_id=case.finding_id
            )
        return self._remediation_repository.get_oqi3_finding_state(
            tenant_id=case.tenant_id, finding_id=case.finding_id
        )


def _as_rejected(run: AgentRun, *, reason: str) -> AgentRun:
    """A rejected-but-well-formed run keeps its `raw_output` (CDD-043
    §18: raw_output is stored whenever the output parses as well-formed
    JSON, regardless of whether its content passes validation) and simply
    carries `result_state=REJECTED_OUTPUT` plus the closed rejection
    reason as `failure_reason` -- the same immutable row identity
    (`run_id`), never a second row and never an in-place mutation of a
    persisted run (this rebuild happens entirely in memory before the
    first, and only, `save_run` call for this `run_id`)."""
    return AgentRun(
        run_id=run.run_id,
        tenant_id=run.tenant_id,
        case_id=run.case_id,
        role_id=run.role_id,
        role_version=run.role_version,
        provider=run.provider,
        model=run.model,
        evidence_packet_digest=run.evidence_packet_digest,
        raw_output=run.raw_output,
        result_state=AgentRunResultState.REJECTED_OUTPUT,
        failure_reason=reason,
        created_on=run.created_on,
    )
