"""CDD-045 -- OQI7-I1 backend-owned semantic aggregation (CDD-045 §22,
§27). The sole place OQI7 "decides meaning": composes read models from the
closed, unmodified OQI1-6 domain capability into the exact field-level
contracts CDD-045 §23 freezes. Reads OQI1-6 ORM classes directly where no
existing domain-repository method already exposes the needed read -- this
repository's own established precedent (`OqiBusinessImpactRepositoryImpl`'s
own docstring: "reading another domain's ORM class directly, without
modifying its owning file, is this repository's own established
precedent"). Writes nothing except the two thin authorization-action
wrappers, which call OQI5-I1's existing `OqiRemediationService` methods
without reimplementing digest/staleness/one-time-consumption logic
(CDD-045 §63, §26).

No model provider is imported or invoked anywhere in this file (CDD-045
§109-110: product reads never trigger agent reasoning). No
`trust_score`/`quality_score`/`confidence_score`/`revenue_at_risk`/
`monetary_impact` field is computed anywhere here (CDD-045 §8, §26)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.oqi_remediation_service import OqiRemediationService
from app.domain.oqi_business_impact.dependency import Criticality
from app.domain.oqi_business_impact.impact import BusinessImpactOutcome
from app.domain.oqi_business_impact.reliance import RelianceState
from app.domain.oqi_finding_origin.origin import FindingStorageFamily
from app.domain.oqi_ontology_impact.evaluation import (
    CurrentImpactStatus,
    FindingFamily,
    ImpactClass,
    ImpactOutcome,
    OntologyElementType,
)
from app.domain.oqi_remediation.case import FindingFamily as RemediationFindingFamily
from app.domain.oqi_remediation.case import derive_remediation_case_id
from app.domain.oqi_remediation_agent.role import AgentRoleId
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.oqi_business_impact import (
    CurrentRelianceORM,
    OqiRelianceEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_integrity import (
    IntegrityReferenceFindingORM,
    IntegrityStructuralFindingORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationCaseORM,
    OqiRemediationInstructionORM,
)
from app.infrastructure.persistence.models.oqi_remediation_agent import (
    AgentAssessmentORM,
    AgentRecommendationORM,
    AgentRunORM,
)
from app.infrastructure.persistence.models.oqi_timeliness import TimelinessFindingORM
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    FindingNotFoundError,
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)

_SPECIALIST_ROLE_IDS: tuple[AgentRoleId, ...] = (
    AgentRoleId.EVIDENCE_CONSISTENCY_ANALYST,
    AgentRoleId.IMPACT_CONTINUITY_ANALYST,
)


class OqiProductExperienceNotFoundError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedFinding:
    family: FindingFamily
    finding_id: UUID
    condition_label: str
    status: str
    state_revision: int
    first_seen_at: datetime
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class FindingSummaryRow:
    finding: ResolvedFinding
    affected_entity_id: UUID | None
    affected_entity_type: str | None
    highest_criticality: Criticality | None
    reliance_state: RelianceState | None


@dataclass(frozen=True, slots=True)
class EvidenceParticipantRow:
    source_system: str
    observed_value: str | None
    is_missing: bool
    is_authoritative: bool
    is_conflicting: bool


@dataclass(frozen=True, slots=True)
class EvidenceCandidateRow:
    candidate_id: UUID
    proposed_value: str
    supporting_participant_count: int


@dataclass(frozen=True, slots=True)
class OntologyImpactPathRow:
    relationship_instance_id: UUID
    path_ordinal: int
    direction: str


@dataclass(frozen=True, slots=True)
class OntologyImpactRow:
    outcome: ImpactOutcome
    direct_entity_id: UUID | None
    direct_entity_type: OntologyElementType | None
    propagated_path: tuple[OntologyImpactPathRow, ...] | None


@dataclass(frozen=True, slots=True)
class BusinessImpactDependencyRow:
    business_process_name: str
    criticality: Criticality | None
    business_dependency_version: int


@dataclass(frozen=True, slots=True)
class BusinessImpactRow:
    outcome: BusinessImpactOutcome
    dependencies: tuple[BusinessImpactDependencyRow, ...]


@dataclass(frozen=True, slots=True)
class RelianceHistoryRow:
    state: RelianceState
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class RelianceRow:
    state: RelianceState
    reason_codes: tuple[str, ...]
    contributing_finding_ids: tuple[UUID, ...]
    history: tuple[RelianceHistoryRow, ...]


@dataclass(frozen=True, slots=True)
class SpecialistAssessmentRow:
    role_id: str
    result_state: str
    assessment_text: str | None
    referenced_candidate_id: UUID | None


@dataclass(frozen=True, slots=True)
class AgentRecommendationRow:
    recommendation_type: str
    candidate_id: UUID | None
    rationale: str
    basis: str


@dataclass(frozen=True, slots=True)
class AgentInvestigationRow:
    specialists: tuple[SpecialistAssessmentRow, ...]
    recommendation: AgentRecommendationRow | None


@dataclass(frozen=True, slots=True)
class RemediationCandidateRow:
    candidate_id: UUID
    proposed_value: str


@dataclass(frozen=True, slots=True)
class RemediationAuthorizationRow:
    authorization_id: UUID
    principal: str
    decided_on: datetime | None
    instruction: str
    authorized_against_state_revision: int
    is_stale: bool
    status: str


@dataclass(frozen=True, slots=True)
class RemediationExternalExecutionRow:
    reported_at: datetime


@dataclass(frozen=True, slots=True)
class RemediationRow:
    case_status: str | None
    candidate: RemediationCandidateRow | None
    recommendation: AgentRecommendationRow | None
    authorization: RemediationAuthorizationRow | None
    external_execution: RemediationExternalExecutionRow | None


@dataclass(frozen=True, slots=True)
class CommandCenterRow:
    reliance_supported_count: int
    reliance_at_risk_count: int
    reliance_unknown_count: int
    critical_dependencies_at_risk_count: int
    open_findings_count: int
    active_agent_investigations_count: int
    pending_human_authorizations_count: int


class OqiProductExperienceService:
    """Read-only composition layer, plus two thin action wrappers. Every
    method is tenant-scoped from its `tenant_id` argument -- the caller
    (the router) supplies this exclusively from
    `TrustedPrincipal.tenant_id`, never from a client-controlled
    parameter (CDD-045 §22)."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._impact_repo = OqiOntologyImpactEvaluationRepositoryImpl(session)
        self._business_impact_repo = OqiBusinessImpactRepositoryImpl(session)
        self._remediation_repo = OqiRemediationRepositoryImpl(session)

    # ------------------------------------------------------------------
    # Command Center (CDD-045 §7, §23).
    # ------------------------------------------------------------------

    def get_command_center(self, *, tenant_id: str) -> CommandCenterRow:
        reliance_counts = {state: 0 for state in RelianceState}
        rows = self.session.execute(
            select(OqiRelianceEvaluationORM.state)
            .join(
                CurrentRelianceORM,
                CurrentRelianceORM.latest_evaluation_id == OqiRelianceEvaluationORM.evaluation_id,
            )
            .where(CurrentRelianceORM.tenant_id == tenant_id)
        ).all()
        for (state_value,) in rows:
            reliance_counts[RelianceState(state_value)] += 1

        critical_at_risk = 0
        at_risk_subjects = self.session.execute(
            select(CurrentRelianceORM.ontology_element_type, CurrentRelianceORM.ontology_element_id)
            .join(
                OqiRelianceEvaluationORM,
                CurrentRelianceORM.latest_evaluation_id == OqiRelianceEvaluationORM.evaluation_id,
            )
            .where(
                CurrentRelianceORM.tenant_id == tenant_id,
                OqiRelianceEvaluationORM.state == RelianceState.RELIANCE_AT_RISK.value,
            )
        ).all()
        for element_type, element_id in at_risk_subjects:
            deps = self._business_impact_repo.list_active_dependencies_for_subject(
                tenant_id=tenant_id,
                ontology_element_type=OntologyElementType(element_type),
                ontology_element_id=element_id,
            )
            if any(dep.criticality is Criticality.CRITICAL for dep in deps):
                critical_at_risk += 1

        open_findings = 0
        for count_query in (
            select(QualityFindingORM.finding_id).where(
                QualityFindingORM.tenant_id == tenant_id, QualityFindingORM.status == "OPEN"
            ),
            select(QualityComparisonFindingORM.finding_id).where(
                QualityComparisonFindingORM.tenant_id == tenant_id,
                QualityComparisonFindingORM.status == "OPEN",
            ),
            select(BusinessRuleFindingORM.finding_id).where(
                BusinessRuleFindingORM.tenant_id == tenant_id,
                BusinessRuleFindingORM.status == "OPEN",
            ),
        ):
            open_findings += len(self.session.execute(count_query).scalars().all())

        active_investigations = (
            self.session.execute(
                select(AgentRunORM.run_id)
                .outerjoin(
                    AgentRecommendationORM, AgentRecommendationORM.run_id == AgentRunORM.run_id
                )
                .where(
                    AgentRunORM.tenant_id == tenant_id,
                    AgentRunORM.role_id == AgentRoleId.RECOMMENDATION_SYNTHESIZER.value,
                    AgentRecommendationORM.recommendation_id.is_(None),
                )
            )
            .scalars()
            .all()
            .__len__()
        )

        pending_authorizations = (
            self.session.execute(
                select(OqiRemediationInstructionORM.instruction_id)
                .join(
                    OqiRemediationCaseORM,
                    OqiRemediationCaseORM.case_id == OqiRemediationInstructionORM.case_id,
                )
                .where(OqiRemediationCaseORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
            .__len__()
        )
        # Pending is authoritatively determined by authorization status,
        # not instruction existence -- recompute precisely.
        from app.infrastructure.persistence.models.oqi_remediation import (
            OqiRemediationAuthorizationORM,
        )

        pending_authorizations = (
            self.session.execute(
                select(OqiRemediationAuthorizationORM.authorization_id)
                .join(
                    OqiRemediationInstructionORM,
                    OqiRemediationInstructionORM.instruction_id
                    == OqiRemediationAuthorizationORM.instruction_id,
                )
                .where(
                    OqiRemediationAuthorizationORM.tenant_id == tenant_id,
                    OqiRemediationAuthorizationORM.status == "PENDING",
                )
            )
            .scalars()
            .all()
            .__len__()
        )

        return CommandCenterRow(
            reliance_supported_count=reliance_counts[RelianceState.RELIANCE_SUPPORTED],
            reliance_at_risk_count=reliance_counts[RelianceState.RELIANCE_AT_RISK],
            reliance_unknown_count=reliance_counts[RelianceState.RELIANCE_UNKNOWN],
            critical_dependencies_at_risk_count=critical_at_risk,
            open_findings_count=open_findings,
            active_agent_investigations_count=active_investigations,
            pending_human_authorizations_count=pending_authorizations,
        )

    # ------------------------------------------------------------------
    # Finding resolution (shared by every per-Finding contract below).
    # ------------------------------------------------------------------

    def _resolve_finding(self, *, tenant_id: str, finding_id: UUID) -> ResolvedFinding | None:
        model = self.session.get(QualityFindingORM, finding_id)
        if model is not None and model.tenant_id == tenant_id:
            return ResolvedFinding(
                family=FindingFamily.OQI1,
                finding_id=finding_id,
                condition_label=model.quality_condition_id,
                status=model.status,
                state_revision=model.state_revision,
                first_seen_at=model.first_seen_at,
                last_seen_at=model.last_seen_at,
            )
        comparison_model = self.session.get(QualityComparisonFindingORM, finding_id)
        if comparison_model is not None and comparison_model.tenant_id == tenant_id:
            return ResolvedFinding(
                family=FindingFamily.OQI2,
                finding_id=finding_id,
                condition_label=comparison_model.quality_condition_id,
                status=comparison_model.status,
                state_revision=comparison_model.state_revision,
                first_seen_at=comparison_model.first_seen_at,
                last_seen_at=comparison_model.last_seen_at,
            )
        rule_model = self.session.get(BusinessRuleFindingORM, finding_id)
        if rule_model is not None and rule_model.tenant_id == tenant_id:
            return ResolvedFinding(
                family=FindingFamily.OQI3,
                finding_id=finding_id,
                condition_label=rule_model.business_condition_id,
                status=rule_model.status,
                state_revision=rule_model.state_revision,
                first_seen_at=rule_model.first_seen_at,
                last_seen_at=rule_model.last_seen_at,
            )
        return None

    def _resolve_entity(
        self, *, tenant_id: str, family: FindingFamily, finding_id: UUID
    ) -> UUID | None:
        try:
            subject = self._impact_repo.resolve_finding_subject(
                tenant_id=tenant_id, finding_family=family, finding_id=finding_id
            )
        except FindingNotFoundError:
            return None
        result = self._impact_repo.resolve_direct_impact(
            tenant_id=tenant_id, source_object_ids=subject.source_object_ids
        )
        return result.entity_id

    # ------------------------------------------------------------------
    # Finding list / detail (CDD-045 §10, §23).
    # ------------------------------------------------------------------

    def list_findings(
        self,
        *,
        tenant_id: str,
        family: str | None,
        status: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[tuple[FindingSummaryRow, ...], str | None]:
        if limit < 1 or limit > 200:
            raise ValidationException("limit must be between 1 and 200")
        offset = int(cursor) if cursor else 0
        resolved: list[ResolvedFinding] = []

        if family is None or family == FindingFamily.OQI1.value:
            query1 = select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
            if status is not None:
                query1 = query1.where(QualityFindingORM.status == status)
            for model1 in self.session.execute(query1).scalars().all():
                resolved.append(
                    ResolvedFinding(
                        family=FindingFamily.OQI1,
                        finding_id=model1.finding_id,
                        condition_label=model1.quality_condition_id,
                        status=model1.status,
                        state_revision=model1.state_revision,
                        first_seen_at=model1.first_seen_at,
                        last_seen_at=model1.last_seen_at,
                    )
                )

        if family is None or family == FindingFamily.OQI2.value:
            query2 = select(QualityComparisonFindingORM).where(
                QualityComparisonFindingORM.tenant_id == tenant_id
            )
            if status is not None:
                query2 = query2.where(QualityComparisonFindingORM.status == status)
            for model2 in self.session.execute(query2).scalars().all():
                resolved.append(
                    ResolvedFinding(
                        family=FindingFamily.OQI2,
                        finding_id=model2.finding_id,
                        condition_label=model2.quality_condition_id,
                        status=model2.status,
                        state_revision=model2.state_revision,
                        first_seen_at=model2.first_seen_at,
                        last_seen_at=model2.last_seen_at,
                    )
                )

        if family is None or family == FindingFamily.OQI3.value:
            query3 = select(BusinessRuleFindingORM).where(
                BusinessRuleFindingORM.tenant_id == tenant_id
            )
            if status is not None:
                query3 = query3.where(BusinessRuleFindingORM.status == status)
            for model3 in self.session.execute(query3).scalars().all():
                resolved.append(
                    ResolvedFinding(
                        family=FindingFamily.OQI3,
                        finding_id=model3.finding_id,
                        condition_label=model3.business_condition_id,
                        status=model3.status,
                        state_revision=model3.state_revision,
                        first_seen_at=model3.first_seen_at,
                        last_seen_at=model3.last_seen_at,
                    )
                )
        # CDD-051 §26 (OQI-H5-I2): closes the pre-existing H4 product-
        # visibility gap for FindingStorageFamily.INTEGRITY, and adds
        # FindingStorageFamily.TIMELINESS -- visibility only, no evaluation
        # semantic change to either dimension. `condition_label` is the
        # Finding's own `finding_type` (no `quality_condition_id`-shaped
        # label exists for these families).
        if family is None or family == FindingStorageFamily.INTEGRITY.value:
            query_structural = select(IntegrityStructuralFindingORM).where(
                IntegrityStructuralFindingORM.tenant_id == tenant_id
            )
            if status is not None:
                query_structural = query_structural.where(
                    IntegrityStructuralFindingORM.status == status
                )
            for model_structural in self.session.execute(query_structural).scalars().all():
                resolved.append(
                    ResolvedFinding(
                        # ResolvedFinding.family's declared type stays the
                        # closed FindingFamily (unmodified, CDD-051 §26) --
                        # FindingStorageFamily.INTEGRITY is a deliberate,
                        # narrowly-scoped runtime-only widening, contained
                        # entirely within these three new list_findings
                        # branches; every other method/call site keeps its
                        # exact existing FindingFamily-only contract.
                        family=FindingStorageFamily.INTEGRITY,  # type: ignore[arg-type]
                        finding_id=model_structural.finding_id,
                        condition_label=model_structural.finding_type,
                        status=model_structural.status,
                        state_revision=model_structural.state_revision,
                        first_seen_at=model_structural.first_seen_at,
                        last_seen_at=model_structural.last_seen_at,
                    )
                )
            query_reference = select(IntegrityReferenceFindingORM).where(
                IntegrityReferenceFindingORM.tenant_id == tenant_id
            )
            if status is not None:
                query_reference = query_reference.where(
                    IntegrityReferenceFindingORM.status == status
                )
            for model_reference in self.session.execute(query_reference).scalars().all():
                resolved.append(
                    ResolvedFinding(
                        # ResolvedFinding.family's declared type stays the
                        # closed FindingFamily (unmodified, CDD-051 §26) --
                        # FindingStorageFamily.INTEGRITY is a deliberate,
                        # narrowly-scoped runtime-only widening, contained
                        # entirely within these three new list_findings
                        # branches; every other method/call site keeps its
                        # exact existing FindingFamily-only contract.
                        family=FindingStorageFamily.INTEGRITY,  # type: ignore[arg-type]
                        finding_id=model_reference.finding_id,
                        condition_label=model_reference.finding_type,
                        status=model_reference.status,
                        state_revision=model_reference.state_revision,
                        first_seen_at=model_reference.first_seen_at,
                        last_seen_at=model_reference.last_seen_at,
                    )
                )

        if family is None or family == FindingStorageFamily.TIMELINESS.value:
            query5 = select(TimelinessFindingORM).where(TimelinessFindingORM.tenant_id == tenant_id)
            if status is not None:
                query5 = query5.where(TimelinessFindingORM.status == status)
            for model5 in self.session.execute(query5).scalars().all():
                resolved.append(
                    ResolvedFinding(
                        family=FindingStorageFamily.TIMELINESS,  # type: ignore[arg-type]
                        finding_id=model5.finding_id,
                        condition_label=model5.finding_type,
                        status=model5.status,
                        state_revision=model5.state_revision,
                        first_seen_at=model5.first_seen_at,
                        last_seen_at=model5.last_seen_at,
                    )
                )

        resolved.sort(key=lambda r: (r.last_seen_at, str(r.finding_id)), reverse=True)
        page = resolved[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(resolved) else None

        rows: list[FindingSummaryRow] = []
        for finding in page:
            # CDD-051 §26: `_resolve_entity` stays untouched, permanently
            # scoped to the closed FindingFamily (OQI1/OQI2/OQI3) vocabulary
            # -- INTEGRITY/TIMELINESS resolve entity impact via their own
            # additive OQI4 resolver methods instead (CDD-050 §20, CDD-051
            # §22), mirrored here rather than inside `_resolve_entity`.
            entity_id: UUID | None
            if isinstance(finding.family, FindingFamily):
                entity_id = self._resolve_entity(
                    tenant_id=tenant_id, family=finding.family, finding_id=finding.finding_id
                )
            elif finding.family is FindingStorageFamily.INTEGRITY:
                entity_id = None
                try:
                    entity_id = self._impact_repo.resolve_integrity_structural_finding_subject(
                        tenant_id=tenant_id, finding_id=finding.finding_id
                    ).entity_id
                except FindingNotFoundError:
                    try:
                        result = self._impact_repo.resolve_integrity_reference_finding_subject(
                            tenant_id=tenant_id, finding_id=finding.finding_id
                        )
                        entity_id = result.entity_id
                    except FindingNotFoundError:
                        entity_id = None
            else:
                entity_id = None
                try:
                    result = self._impact_repo.resolve_timeliness_finding_subject(
                        tenant_id=tenant_id, finding_id=finding.finding_id
                    )
                    entity_id = result.entity_id
                except FindingNotFoundError:
                    entity_id = None
            highest: Criticality | None = None
            reliance_state: RelianceState | None = None
            entity_type: str | None = None
            if entity_id is not None:
                entity_type = OntologyElementType.ENTITY.value
                deps = self._business_impact_repo.list_active_dependencies_for_subject(
                    tenant_id=tenant_id,
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=entity_id,
                )
                ranked = [dep.criticality for dep in deps if dep.criticality is not None]
                if ranked:
                    from app.domain.oqi_business_impact.dependency import criticality_sort_key

                    highest = max(ranked, key=criticality_sort_key)
                current = self.session.get(
                    CurrentRelianceORM,
                    (tenant_id, OntologyElementType.ENTITY.value, entity_id),
                )
                if current is not None:
                    evaluation = self.session.get(
                        OqiRelianceEvaluationORM, current.latest_evaluation_id
                    )
                    if evaluation is not None:
                        reliance_state = RelianceState(evaluation.state)
            rows.append(
                FindingSummaryRow(
                    finding=finding,
                    affected_entity_id=entity_id,
                    affected_entity_type=entity_type,
                    highest_criticality=highest,
                    reliance_state=reliance_state,
                )
            )
        return tuple(rows), next_cursor

    def get_finding_detail(self, *, tenant_id: str, finding_id: UUID) -> ResolvedFinding | None:
        return self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)

    # ------------------------------------------------------------------
    # Evidence (CDD-045 §11, §23).
    # ------------------------------------------------------------------

    def get_evidence(
        self, *, tenant_id: str, finding_id: UUID
    ) -> EvidenceParticipantsBundle | None:
        finding = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
        if finding is None:
            return None
        participants: tuple[EvidenceParticipantRow, ...] = ()
        candidate: EvidenceCandidateRow | None = None
        if finding.family is FindingFamily.OQI2:
            model = self.session.get(QualityComparisonFindingORM, finding_id)
            assert model is not None
            observations = OqiRemediationParticipantReader(
                self.session
            ).load_participant_observations(model.latest_evaluation_id)
            participants = tuple(
                EvidenceParticipantRow(
                    source_system=obs.role,
                    observed_value=obs.observed_value,
                    is_missing=obs.is_missing,
                    is_authoritative=obs.authoritative,
                    is_conflicting=obs.is_conflicting,
                )
                for obs in observations
            )
        case = self._remediation_repo.get_case(
            tenant_id=tenant_id,
            finding_family=RemediationFindingFamily(finding.family.value),
            finding_id=finding_id,
        )
        if case is not None:
            candidates = self._remediation_repo.get_candidates_for_case(case.case_id)
            if candidates:
                top = candidates[0]
                candidate = EvidenceCandidateRow(
                    candidate_id=top.candidate_id,
                    proposed_value=top.proposed_value,
                    supporting_participant_count=len(top.supporting_evidence_ids),
                )
        return EvidenceParticipantsBundle(participants=participants, candidate=candidate)

    # ------------------------------------------------------------------
    # Ontology Impact (CDD-045 §12, §23).
    # ------------------------------------------------------------------

    def get_ontology_impact(self, *, tenant_id: str, finding_id: UUID) -> OntologyImpactRow | None:
        finding = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
        if finding is None:
            return None
        rows = self._impact_repo.get_current_impacts_for_finding(
            tenant_id=tenant_id, finding_family=finding.family, finding_id=finding_id
        )
        active = [row for row in rows if row.status is CurrentImpactStatus.ACTIVE]
        resolved = [row for row in rows if row.status is CurrentImpactStatus.RESOLVED]
        if not active and not resolved:
            # Absence is not proof of no impact -- may be IMPACT_UNKNOWN or
            # a first-time NO_IMPACT, indistinguishable from a current-
            # projection row alone (verified against
            # OqiOntologyImpactEvaluationService._apply_current_projection
            # at OQI6-VM time). Never guess; report UNKNOWN.
            return OntologyImpactRow(
                outcome=ImpactOutcome.IMPACT_UNKNOWN,
                direct_entity_id=None,
                direct_entity_type=None,
                propagated_path=None,
            )
        if not active:
            return OntologyImpactRow(
                outcome=ImpactOutcome.NO_IMPACT,
                direct_entity_id=None,
                direct_entity_type=None,
                propagated_path=None,
            )
        direct_rows = [row for row in active if row.impact_kind is ImpactClass.DIRECT]
        propagated_rows = [row for row in active if row.impact_kind is ImpactClass.PROPAGATED]
        direct_entity_id = direct_rows[0].ontology_element_id if direct_rows else None
        direct_entity_type = direct_rows[0].ontology_element_type if direct_rows else None
        propagated_path: tuple[OntologyImpactPathRow, ...] | None = None
        if propagated_rows:
            evaluation = self._impact_repo.get_evaluation(propagated_rows[0].latest_evaluation_id)
            if evaluation is not None:
                propagated_path = tuple(
                    OntologyImpactPathRow(
                        relationship_instance_id=path.institutional_relationship_id,
                        path_ordinal=path.path_ordinal,
                        direction=path.direction,
                    )
                    for path in sorted(evaluation.paths, key=lambda p: p.path_ordinal)
                    if path.ontology_element_id == propagated_rows[0].ontology_element_id
                )
        return OntologyImpactRow(
            outcome=ImpactOutcome.IMPACTED,
            direct_entity_id=direct_entity_id,
            direct_entity_type=direct_entity_type,
            propagated_path=propagated_path,
        )

    # ------------------------------------------------------------------
    # Business Impact (CDD-045 §13, §23).
    # ------------------------------------------------------------------

    def get_business_impact(self, *, tenant_id: str, finding_id: UUID) -> BusinessImpactRow | None:
        finding = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
        if finding is None:
            return None
        entity_id = self._resolve_entity(
            tenant_id=tenant_id, family=finding.family, finding_id=finding_id
        )
        if entity_id is None:
            return BusinessImpactRow(
                outcome=BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN, dependencies=()
            )
        dependencies = self._business_impact_repo.list_active_dependencies_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
        )
        impact_status = self._business_impact_repo.get_current_impact_status_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
        )
        from app.domain.oqi_business_impact.impact import derive_business_impact_outcome

        outcome = derive_business_impact_outcome(
            active_dependency_exists=bool(dependencies), impact_status=impact_status
        )
        dependency_rows: list[BusinessImpactDependencyRow] = []
        for dep in dependencies:
            process = self._business_impact_repo.get_latest_business_process(
                tenant_id=tenant_id, process_id=dep.business_process_id
            )
            dependency_rows.append(
                BusinessImpactDependencyRow(
                    business_process_name=process.name if process is not None else "Unknown",
                    criticality=dep.criticality,
                    business_dependency_version=dep.version,
                )
            )
        return BusinessImpactRow(outcome=outcome, dependencies=tuple(dependency_rows))

    # ------------------------------------------------------------------
    # Reliance (CDD-045 §16, §23).
    # ------------------------------------------------------------------

    def get_reliance(self, *, tenant_id: str, finding_id: UUID) -> RelianceRow | None:
        finding = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
        if finding is None:
            return None
        entity_id = self._resolve_entity(
            tenant_id=tenant_id, family=finding.family, finding_id=finding_id
        )
        if entity_id is None:
            return RelianceRow(
                state=RelianceState.RELIANCE_UNKNOWN,
                reason_codes=("ONTOLOGY_IMPACT_UNKNOWN",),
                contributing_finding_ids=(finding_id,),
                history=(),
            )
        current = self.session.get(
            CurrentRelianceORM, (tenant_id, OntologyElementType.ENTITY.value, entity_id)
        )
        if current is None:
            return RelianceRow(
                state=RelianceState.RELIANCE_UNKNOWN,
                reason_codes=("INSUFFICIENT_QUALITY_COVERAGE",),
                contributing_finding_ids=(),
                history=(),
            )
        evaluation = self.session.get(OqiRelianceEvaluationORM, current.latest_evaluation_id)
        assert evaluation is not None
        history_rows = (
            self.session.execute(
                select(OqiRelianceEvaluationORM)
                .where(
                    OqiRelianceEvaluationORM.tenant_id == tenant_id,
                    OqiRelianceEvaluationORM.ontology_element_type
                    == OntologyElementType.ENTITY.value,
                    OqiRelianceEvaluationORM.ontology_element_id == entity_id,
                )
                .order_by(OqiRelianceEvaluationORM.evaluated_at)
            )
            .scalars()
            .all()
        )
        return RelianceRow(
            state=RelianceState(evaluation.state),
            reason_codes=tuple(evaluation.reason_codes),
            contributing_finding_ids=(finding_id,),
            history=tuple(
                RelianceHistoryRow(state=RelianceState(row.state), evaluated_at=row.evaluated_at)
                for row in history_rows
            ),
        )

    # ------------------------------------------------------------------
    # Agent Investigation (CDD-045 §18, §23).
    # ------------------------------------------------------------------

    def get_agent_investigation(
        self, *, tenant_id: str, finding_id: UUID
    ) -> AgentInvestigationRow | None:
        finding = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
        if finding is None:
            return None
        case_id = derive_remediation_case_id(
            tenant_id=tenant_id,
            finding_family=RemediationFindingFamily(finding.family.value),
            finding_id=finding_id,
        )
        case_exists = self.session.get(OqiRemediationCaseORM, case_id) is not None
        if not case_exists:
            return AgentInvestigationRow(specialists=(), recommendation=None)

        specialists: list[SpecialistAssessmentRow] = []
        for role_id in _SPECIALIST_ROLE_IDS:
            run = self.session.execute(
                select(AgentRunORM)
                .where(
                    AgentRunORM.tenant_id == tenant_id,
                    AgentRunORM.case_id == case_id,
                    AgentRunORM.role_id == role_id.value,
                )
                .order_by(AgentRunORM.created_on.desc())
                .limit(1)
            ).scalar_one_or_none()
            if run is None:
                continue
            assessment = self.session.get(AgentAssessmentORM, run.run_id)
            specialists.append(
                SpecialistAssessmentRow(
                    role_id=role_id.value,
                    result_state=run.result_state,
                    assessment_text=assessment.rationale if assessment is not None else None,
                    referenced_candidate_id=(
                        assessment.candidate_id if assessment is not None else None
                    ),
                )
            )

        recommendation_row: AgentRecommendationRow | None = None
        latest_recommendation = self.session.execute(
            select(AgentRecommendationORM)
            .where(AgentRecommendationORM.case_id == case_id)
            .order_by(AgentRecommendationORM.created_on.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest_recommendation is not None:
            specialist_supported = all(
                specialist.assessment_text is not None for specialist in specialists
            ) and len(specialists) == len(_SPECIALIST_ROLE_IDS)
            recommendation_row = AgentRecommendationRow(
                recommendation_type=latest_recommendation.recommendation_type,
                candidate_id=latest_recommendation.candidate_id,
                rationale=latest_recommendation.rationale,
                basis="SPECIALIST_SUPPORTED" if specialist_supported else "SYNTHESIZER_ONLY",
            )
        return AgentInvestigationRow(
            specialists=tuple(specialists), recommendation=recommendation_row
        )

    # ------------------------------------------------------------------
    # Remediation (CDD-045 §19-§20, §23).
    # ------------------------------------------------------------------

    def get_remediation(self, *, tenant_id: str, finding_id: UUID) -> RemediationRow | None:
        finding = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
        if finding is None:
            return None
        case = self._remediation_repo.get_case(
            tenant_id=tenant_id,
            finding_family=RemediationFindingFamily(finding.family.value),
            finding_id=finding_id,
        )
        if case is None:
            return RemediationRow(
                case_status=None,
                candidate=None,
                recommendation=None,
                authorization=None,
                external_execution=None,
            )
        candidate_row: RemediationCandidateRow | None = None
        candidates = self._remediation_repo.get_candidates_for_case(case.case_id)
        if candidates:
            candidate_row = RemediationCandidateRow(
                candidate_id=candidates[0].candidate_id, proposed_value=candidates[0].proposed_value
            )

        agent_investigation = self.get_agent_investigation(
            tenant_id=tenant_id, finding_id=finding_id
        )
        recommendation_row = agent_investigation.recommendation if agent_investigation else None

        authorization_row: RemediationAuthorizationRow | None = None
        instruction = self.session.execute(
            select(OqiRemediationInstructionORM)
            .where(OqiRemediationInstructionORM.case_id == case.case_id)
            .order_by(OqiRemediationInstructionORM.created_on.desc())
            .limit(1)
        ).scalar_one_or_none()
        if instruction is not None:
            from app.infrastructure.persistence.models.oqi_remediation import (
                OqiRemediationAuthorizationORM,
            )

            authorization = self.session.execute(
                select(OqiRemediationAuthorizationORM)
                .where(OqiRemediationAuthorizationORM.instruction_id == instruction.instruction_id)
                .order_by(OqiRemediationAuthorizationORM.requested_on.desc())
                .limit(1)
            ).scalar_one_or_none()
            if authorization is not None:
                live_finding = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
                is_stale = (
                    live_finding is not None
                    and live_finding.state_revision != instruction.finding_state_revision
                )
                authorization_row = RemediationAuthorizationRow(
                    authorization_id=authorization.authorization_id,
                    principal=authorization.decided_by or authorization.requested_by,
                    decided_on=authorization.decided_on,
                    instruction=instruction.action_type,
                    authorized_against_state_revision=instruction.finding_state_revision,
                    is_stale=is_stale,
                    status=authorization.status,
                )

        external_execution_row: RemediationExternalExecutionRow | None = None
        if case.external_execution_claimed and case.external_execution_claimed_on is not None:
            external_execution_row = RemediationExternalExecutionRow(
                reported_at=case.external_execution_claimed_on
            )

        return RemediationRow(
            case_status=case.status.value,
            candidate=candidate_row,
            recommendation=recommendation_row,
            authorization=authorization_row,
            external_execution=external_execution_row,
        )

    # ------------------------------------------------------------------
    # Actions (CDD-045 §23 "Actions", §63 -- transport only, zero new
    # authority; calls OQI5-I1's existing OqiRemediationService methods
    # verbatim).
    # ------------------------------------------------------------------

    def decide_authorization(
        self,
        *,
        tenant_id: str,
        authorization_id: UUID,
        approve: bool,
        decided_by: str,
        rejection_reason: str | None,
    ) -> str:
        service = OqiRemediationService(
            repository=self._remediation_repo,
            participant_reader=OqiRemediationParticipantReader(self.session),
        )
        if approve:
            authorization = service.approve(
                tenant_id=tenant_id, authorization_id=authorization_id, decided_by=decided_by
            )
        else:
            authorization = service.reject(
                tenant_id=tenant_id,
                authorization_id=authorization_id,
                decided_by=decided_by,
                rejection_reason=rejection_reason or "rejected",
            )
        return authorization.status.value

    def report_execution(self, *, tenant_id: str, authorization_id: UUID) -> str:
        service = OqiRemediationService(
            repository=self._remediation_repo,
            participant_reader=OqiRemediationParticipantReader(self.session),
        )
        case = service.report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        return case.status.value


@dataclass(frozen=True, slots=True)
class EvidenceParticipantsBundle:
    participants: tuple[EvidenceParticipantRow, ...]
    candidate: EvidenceCandidateRow | None
