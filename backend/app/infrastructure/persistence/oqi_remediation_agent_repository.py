"""Repository for OQI5-I2 -- Governed Real Agent Reasoning (CDD-043
§18-§22; Artifact Authorization §3 row 7). Persists
`AgentRole`/`AgentRun`/`AgentAssessment`/`AgentRecommendation`, and reads
(never writes) existing I1 candidate/participant facts and OQI4 impact
facts needed to deterministically build an `AgentEvidencePacket`.

`OqiRemediationAgentPacketReader` composes I1's own
`OqiRemediationParticipantReader` (read-only reuse, not a copy) with a
read-only OQI4 impact lookup -- no OQI1/2/3/4 or I1 file is modified to
support this."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.oqi_remediation.case import FindingFamily, RemediationCase
from app.domain.oqi_remediation_agent.recommendation import AgentAssessment, AgentRecommendation
from app.domain.oqi_remediation_agent.role import AgentRole, AgentRoleId, RecommendationType
from app.domain.oqi_remediation_agent.run import (
    AgentEvidencePacket,
    AgentRun,
    AgentRunResultState,
    PacketCandidate,
    PacketOntologyImpact,
    PacketParticipant,
)
from app.infrastructure.persistence.models.oqi_ontology_impact_evaluation import (
    CurrentOntologyImpactORM,
    OntologyImpactEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_remediation_agent import (
    AgentAssessmentORM,
    AgentRecommendationORM,
    AgentRoleORM,
    AgentRunORM,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
)

if TYPE_CHECKING:
    from app.domain.oqi_remediation.candidate import RemediationCandidate


class OqiRemediationAgentRepository(Protocol):
    def get_active_role(self, role_id: AgentRoleId) -> AgentRole | None: ...

    def save_role_if_absent(self, role: AgentRole) -> None: ...

    def save_run(self, run: AgentRun) -> None: ...

    def get_run(self, run_id: UUID) -> AgentRun | None: ...

    def save_assessment(self, assessment: AgentAssessment) -> None: ...

    def get_assessments_for_runs(self, run_ids: Sequence[UUID]) -> tuple[AgentAssessment, ...]: ...

    def save_recommendation(self, recommendation: AgentRecommendation) -> None: ...

    def get_recommendation(self, recommendation_id: UUID) -> AgentRecommendation | None: ...


class OqiRemediationAgentRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_role(self, role_id: AgentRoleId) -> AgentRole | None:
        model = (
            self.session.execute(
                select(AgentRoleORM)
                .where(AgentRoleORM.role_id == role_id.value)
                .order_by(AgentRoleORM.version.desc())
            )
            .scalars()
            .first()
        )
        if model is None:
            return None
        return _role_to_domain(model)

    def save_role_if_absent(self, role: AgentRole) -> None:
        existing = self.session.get(AgentRoleORM, (role.role_id.value, role.version))
        if existing is not None:
            return
        self.session.add(_role_to_orm(role))

    def save_run(self, run: AgentRun) -> None:
        if self.session.get(AgentRunORM, run.run_id) is not None:
            return
        self.session.add(_run_to_orm(run))

    def get_run(self, run_id: UUID) -> AgentRun | None:
        model = self.session.get(AgentRunORM, run_id)
        return None if model is None else _run_to_domain(model)

    def save_assessment(self, assessment: AgentAssessment) -> None:
        if self.session.get(AgentAssessmentORM, assessment.run_id) is not None:
            return
        self.session.add(_assessment_to_orm(assessment))

    def get_assessments_for_runs(self, run_ids: Sequence[UUID]) -> tuple[AgentAssessment, ...]:
        if not run_ids:
            return ()
        models = (
            self.session.execute(
                select(AgentAssessmentORM).where(AgentAssessmentORM.run_id.in_(run_ids))
            )
            .scalars()
            .all()
        )
        return tuple(_assessment_to_domain(model) for model in models)

    def save_recommendation(self, recommendation: AgentRecommendation) -> None:
        if self.session.get(AgentRecommendationORM, recommendation.recommendation_id) is not None:
            return
        self.session.add(_recommendation_to_orm(recommendation))

    def get_recommendation(self, recommendation_id: UUID) -> AgentRecommendation | None:
        model = self.session.get(AgentRecommendationORM, recommendation_id)
        return None if model is None else _recommendation_to_domain(model)


class OqiRemediationAgentPacketReader:
    """Deterministic, read-only `AgentEvidencePacket` construction from
    existing persisted I1 candidate/participant facts and OQI4 impact
    facts (CDD-043 §19). Never writes to any table."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._participant_reader = OqiRemediationParticipantReader(session)

    def build_packet(
        self,
        *,
        case: RemediationCase,
        candidates: Sequence[RemediationCandidate],
        finding_state_revision: int,
        evaluation_id: UUID | None,
        role_version: int,
    ) -> AgentEvidencePacket:
        packet_candidates = tuple(
            PacketCandidate(
                candidate_id=c.candidate_id,
                target_source_object_id=c.target_source_object_id,
                target_source_field_id=c.target_source_field_id,
                proposed_value=c.proposed_value,
                supporting_evidence_ids=c.supporting_evidence_ids,
                conflicting_evidence_ids=c.conflicting_evidence_ids,
                basis=c.basis.value,
            )
            for c in candidates
        )

        participants: tuple[PacketParticipant, ...] = ()
        if evaluation_id is not None:
            observations = self._participant_reader.load_participant_observations(evaluation_id)
            participants = tuple(
                PacketParticipant(
                    role=p.role,
                    observed_value=p.observed_value,
                    evidence_id=p.evidence_id,
                    is_conflicting=p.is_conflicting,
                    is_authoritative=p.authoritative,
                )
                for p in observations
            )

        ontology_impacts = self._read_ontology_impacts(
            tenant_id=case.tenant_id, finding_family=case.finding_family, finding_id=case.finding_id
        )

        return AgentEvidencePacket(
            tenant_id=case.tenant_id,
            finding_family=case.finding_family,
            finding_id=case.finding_id,
            finding_state_revision=finding_state_revision,
            case_id=case.case_id,
            evaluation_id=evaluation_id,
            participants=participants,
            candidates=packet_candidates,
            ontology_impacts=ontology_impacts,
            role_version=role_version,
        )

    def _read_ontology_impacts(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> tuple[PacketOntologyImpact, ...]:
        current_rows = (
            self.session.execute(
                select(CurrentOntologyImpactORM).where(
                    CurrentOntologyImpactORM.tenant_id == tenant_id,
                    CurrentOntologyImpactORM.finding_family == finding_family.value,
                    CurrentOntologyImpactORM.finding_id == finding_id,
                )
            )
            .scalars()
            .all()
        )
        results = []
        for row in current_rows:
            evaluation = self.session.get(OntologyImpactEvaluationORM, row.latest_evaluation_id)
            if evaluation is None:
                continue
            results.append(
                PacketOntologyImpact(
                    impact_evaluation_id=evaluation.evaluation_id,
                    ontology_element_type=row.ontology_element_type,
                    ontology_element_id=row.ontology_element_id,
                    impact_kind=row.impact_kind,
                    outcome=evaluation.outcome,
                )
            )
        return tuple(results)


def _role_to_orm(role: AgentRole) -> AgentRoleORM:
    return AgentRoleORM(
        role_id=role.role_id.value,
        version=role.version,
        status=role.status.value,
        instructions=role.instructions,
        allowed_recommendation_types=[t.value for t in role.allowed_recommendation_types],
        created_on=role.created_on,
    )


def _role_to_domain(model: AgentRoleORM) -> AgentRole:
    from app.domain.oqi_remediation_agent.role import AgentRoleStatus

    return AgentRole(
        role_id=AgentRoleId(model.role_id),
        version=model.version,
        status=AgentRoleStatus(model.status),
        instructions=model.instructions,
        allowed_recommendation_types=tuple(
            RecommendationType(t) for t in model.allowed_recommendation_types
        ),
        created_on=model.created_on,
    )


def _run_to_orm(run: AgentRun) -> AgentRunORM:
    return AgentRunORM(
        run_id=run.run_id,
        tenant_id=run.tenant_id,
        case_id=run.case_id,
        role_id=run.role_id,
        role_version=run.role_version,
        provider=run.provider,
        model=run.model,
        evidence_packet_digest=run.evidence_packet_digest,
        raw_output=run.raw_output,
        result_state=run.result_state.value,
        failure_reason=run.failure_reason,
        created_on=run.created_on,
    )


def _run_to_domain(model: AgentRunORM) -> AgentRun:
    return AgentRun(
        run_id=model.run_id,
        tenant_id=model.tenant_id,
        case_id=model.case_id,
        role_id=model.role_id,
        role_version=model.role_version,
        provider=model.provider,
        model=model.model,
        evidence_packet_digest=model.evidence_packet_digest,
        raw_output=model.raw_output,
        result_state=AgentRunResultState(model.result_state),
        failure_reason=model.failure_reason,
        created_on=model.created_on,
    )


def _assessment_to_orm(assessment: AgentAssessment) -> AgentAssessmentORM:
    return AgentAssessmentORM(
        run_id=assessment.run_id,
        role_id=assessment.role_id,
        recommendation_type=assessment.recommendation_type.value,
        candidate_id=assessment.candidate_id,
        supporting_evidence_ids=[str(e) for e in assessment.supporting_evidence_ids],
        conflicting_evidence_ids=[str(e) for e in assessment.conflicting_evidence_ids],
        impact_evaluation_ids=[str(e) for e in assessment.impact_evaluation_ids],
        rationale=assessment.rationale,
    )


def _assessment_to_domain(model: AgentAssessmentORM) -> AgentAssessment:
    return AgentAssessment(
        run_id=model.run_id,
        role_id=model.role_id,
        recommendation_type=RecommendationType(model.recommendation_type),
        candidate_id=model.candidate_id,
        supporting_evidence_ids=tuple(UUID(e) for e in model.supporting_evidence_ids),
        conflicting_evidence_ids=tuple(UUID(e) for e in model.conflicting_evidence_ids),
        impact_evaluation_ids=tuple(UUID(e) for e in model.impact_evaluation_ids),
        rationale=model.rationale,
    )


def _recommendation_to_orm(recommendation: AgentRecommendation) -> AgentRecommendationORM:
    return AgentRecommendationORM(
        recommendation_id=recommendation.recommendation_id,
        run_id=recommendation.run_id,
        case_id=recommendation.case_id,
        recommendation_type=recommendation.recommendation_type.value,
        candidate_id=recommendation.candidate_id,
        supporting_evidence_ids=[str(e) for e in recommendation.supporting_evidence_ids],
        conflicting_evidence_ids=[str(e) for e in recommendation.conflicting_evidence_ids],
        rationale=recommendation.rationale,
        created_on=recommendation.created_on,
    )


def _recommendation_to_domain(model: AgentRecommendationORM) -> AgentRecommendation:
    return AgentRecommendation(
        recommendation_id=model.recommendation_id,
        run_id=model.run_id,
        case_id=model.case_id,
        recommendation_type=RecommendationType(model.recommendation_type),
        candidate_id=model.candidate_id,
        supporting_evidence_ids=tuple(UUID(e) for e in model.supporting_evidence_ids),
        conflicting_evidence_ids=tuple(UUID(e) for e in model.conflicting_evidence_ids),
        rationale=model.rationale,
        created_on=model.created_on,
    )
