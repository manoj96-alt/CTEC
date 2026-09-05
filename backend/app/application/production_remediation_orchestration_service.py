"""Production Governed Remediation Orchestration (CDD-058). Composes the
already-existing, already-verified OQI5-I1 `OqiRemediationService`
(candidate extraction, instruction construction, authorization request) --
never OQI5-I2 agent reasoning, never a live model provider (CDD-058 SS11/
SS20) -- and, after a successful existing `report_external_execution` call,
a new, narrow, remediation-scoped reevaluation composition built entirely
from already-existing per-dimension/OQI4/OQI6/Reliance entrypoints (CDD-058
SS9) -- never `OqiEvaluationOrchestrationService.evaluate()` (CDD-056),
whose request contract remediation's own persisted state cannot honestly
satisfy.

This module introduces zero new domain/authority logic. Every read here
uses `select(...)`/`session.get(...)` (never a `ClassName(...)`
construction against a governed ORM model this file does not itself own),
so no ORM class's single-construction-site invariant is affected.

`AGENT != AUTHORITY`, `RECOMMENDATION != AUTHORIZATION`,
`AUTHORIZATION != EXECUTION`, `EXECUTION != RESOLUTION`,
`REMEDIATION != RESOLUTION` (CDD-058 SS5): this file never creates or
mutates a `RemediationAuthorization` into `APPROVED`/`REJECTED`, never
reports an execution, and never sets a Finding's own status -- Finding
resolution is exclusively a side effect of the existing, unmodified
per-dimension `evaluate_current_state` entrypoints this file calls."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.application.oqi_accuracy_evaluation_service import OqiAccuracyEvaluationService
from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_conformity_evaluation_service import OqiConformityEvaluationService
from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.application.oqi_ontology_impact_evaluation_service import (
    OqiOntologyImpactEvaluationService,
)
from app.application.oqi_reference_evidence_service import OqiReferenceEvidenceService
from app.application.oqi_remediation_service import OqiRemediationError, OqiRemediationService
from app.domain.oqi.evaluation import EvaluationSubject, SourceRecordLineageIdentity
from app.domain.oqi.quality_rule import QualityDimension
from app.domain.oqi_ontology_impact.evaluation import FindingFamily as OntologyImpactFindingFamily
from app.domain.oqi_ontology_impact.evaluation import (
    OntologyElementType,
)
from app.domain.oqi_remediation.case import FindingFamily as RemediationFindingFamily
from app.domain.oqi_remediation.case import derive_remediation_case_id
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
    OqiRemediationInstructionORM,
)
from app.infrastructure.persistence.oqi_accuracy_evaluation_repository import (
    OqiAccuracyEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)
from app.infrastructure.persistence.oqi_canonical_standard_repository import (
    OqiCanonicalStandardRepositoryImpl,
)
from app.infrastructure.persistence.oqi_conformity_evaluation_repository import (
    OqiConformityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
    OqiCrossSourceCorrespondenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
    OqiCrossSourceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OQI_ADVISORY_LOCK_SEED,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import (
    OqiQualityRuleRepositoryImpl,
)
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)

_ACCURACY_QUALITY_DIMENSION = "ACCURACY"
_CONFORMITY_QUALITY_DIMENSION = "CONFORMITY"


class ProductionRemediationOrchestrationError(Exception):
    """Carries one of this module's closed diagnostic codes -- mirrors
    `OqiRemediationError`'s own shape; no raw internal exception escapes
    the public `prepare_remediation` entrypoint."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class CandidateView:
    candidate_id: UUID
    proposed_value: str
    basis: str


@dataclass(frozen=True, slots=True)
class InstructionView:
    instruction_id: UUID
    candidate_id: UUID


@dataclass(frozen=True, slots=True)
class AuthorizationView:
    authorization_id: UUID
    instruction_id: UUID
    status: str


@dataclass(frozen=True, slots=True)
class PrepareRemediationResult:
    correlation_id: UUID | None
    case_id: UUID
    finding_id: UUID
    case_status: str
    candidates: tuple[CandidateView, ...]
    instructions: tuple[InstructionView, ...]
    authorizations: tuple[AuthorizationView, ...]
    agent_reasoning_status: str = "NOT_INVOKED"


@dataclass(frozen=True, slots=True)
class DqReevaluationResult:
    status: str  # "EVALUATED" | "NOT_EVALUABLE" | "FAILED"
    outcome: str | None = None


@dataclass(frozen=True, slots=True)
class OntologyImpactReevaluationResult:
    status: str  # "EVALUATED" | "NOT_ATTEMPTED" | "FAILED"
    outcome: str | None = None


@dataclass(frozen=True, slots=True)
class BusinessImpactReevaluationResult:
    dependency_id: UUID
    status: str
    outcome: str | None = None


@dataclass(frozen=True, slots=True)
class RelianceReevaluationResult:
    status: str
    state: str | None = None


@dataclass(frozen=True, slots=True)
class ReevaluationResult:
    case_id: UUID
    finding_id: UUID
    case_status: str
    dq: DqReevaluationResult
    ontology_impact: OntologyImpactReevaluationResult
    business_impact: tuple[BusinessImpactReevaluationResult, ...] = field(default_factory=tuple)
    reliance: RelianceReevaluationResult = field(
        default_factory=lambda: RelianceReevaluationResult(status="NOT_ATTEMPTED")
    )


class ProductionRemediationOrchestrationService:
    """CDD-058: composition-only orchestrator. Owns no persistence
    semantics of its own beyond the stage-boundary commit/rollback pattern
    documented in this module's own docstring."""

    def __init__(
        self, session: Session, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self.session = session
        self._clock = clock

    # ------------------------------------------------------------------
    # Preparation (CDD-058 SS4/SS7-SS12/SS22).
    # ------------------------------------------------------------------

    def prepare_remediation(
        self,
        *,
        tenant_id: str,
        finding_id: UUID,
        requested_by: str,
        correlation_id: UUID | None = None,
    ) -> PrepareRemediationResult:
        resolved = self._resolve_finding(tenant_id=tenant_id, finding_id=finding_id)
        if resolved is None:
            raise ProductionRemediationOrchestrationError("REMEDIATION_FINDING_NOT_FOUND")
        finding_family, quality_dimension = resolved

        case_id = derive_remediation_case_id(
            tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
        )
        # CDD-058 SS14/SS21-SS23: a transaction-scoped advisory lock keyed
        # on this Finding's own deterministic case identity serializes
        # concurrent `prepare` calls for the identical Finding -- the same
        # `pg_advisory_xact_lock` discipline every other OQI evaluator
        # already uses (never `pg_advisory_lock`, so it releases
        # automatically on commit/rollback/connection loss). This is
        # belt-and-suspenders alongside the repository's own atomic
        # `ON CONFLICT` correction: it also prevents two concurrent callers
        # from each minting a *logically duplicate* (non-colliding, since
        # `uuid4()`-identified) instruction/authorization for the same
        # candidate, which a bare `ON CONFLICT` on the candidate table
        # alone would not prevent -- PROVIDED the lock is held for the
        # entire method, not just its first transaction. An earlier draft
        # committed after `extract_candidates` and again after each
        # `construct_instruction`/`request_authorization` call; since
        # `pg_advisory_xact_lock` releases on every commit, that draft
        # actually released the lock before the instruction/authorization
        # check-then-insert steps ran, leaving exactly the race it was
        # meant to close (`oqi_remediation_instructions` has no unique
        # constraint on `candidate_id`, only on `instruction_id`, so two
        # concurrent callers could each mint a distinct-`uuid4()`
        # instruction for the same candidate). Fixed by acquiring the lock
        # once and deferring every write to a single commit at the very
        # end of this method -- reads of not-yet-committed writes within
        # this same session still see them (SQLAlchemy autoflushes pending
        # writes before a `select()`), so no intermediate commit is needed
        # for correctness, only durability, which the final commit
        # provides.
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {
                "identity": f"production-remediation-prepare:{case_id}",
                "seed": OQI_ADVISORY_LOCK_SEED,
            },
        )

        repository = OqiRemediationRepositoryImpl(self.session)
        service = OqiRemediationService(
            repository=repository,
            participant_reader=OqiRemediationParticipantReader(self.session),
        )
        moment = self._clock()
        try:
            case, candidates = service.extract_candidates(
                tenant_id=tenant_id,
                finding_family=finding_family,
                finding_id=finding_id,
                quality_dimension=quality_dimension,
                now=moment,
            )

            instruction_views: list[InstructionView] = []
            authorization_views: list[AuthorizationView] = []
            for candidate in candidates:
                instruction_id = self.session.execute(
                    select(OqiRemediationInstructionORM.instruction_id)
                    .where(OqiRemediationInstructionORM.candidate_id == candidate.candidate_id)
                    .limit(1)
                ).scalar_one_or_none()
                if instruction_id is None:
                    instruction = service.construct_instruction(
                        tenant_id=tenant_id,
                        candidate_id=candidate.candidate_id,
                        created_by=requested_by,
                        now=self._clock(),
                    )
                    instruction_id = instruction.instruction_id
                instruction_views.append(
                    InstructionView(
                        instruction_id=instruction_id, candidate_id=candidate.candidate_id
                    )
                )

                authorization_id = self.session.execute(
                    select(OqiRemediationAuthorizationORM.authorization_id)
                    .where(OqiRemediationAuthorizationORM.instruction_id == instruction_id)
                    .limit(1)
                ).scalar_one_or_none()
                if authorization_id is None:
                    authorization = service.request_authorization(
                        tenant_id=tenant_id,
                        instruction_id=instruction_id,
                        requested_by=requested_by,
                        now=self._clock(),
                    )
                    authorization_status = authorization.status.value
                    authorization_id = authorization.authorization_id
                else:
                    existing_authorization = repository.get_authorization_by_id(authorization_id)
                    assert existing_authorization is not None
                    authorization_status = existing_authorization.status.value
                authorization_views.append(
                    AuthorizationView(
                        authorization_id=authorization_id,
                        instruction_id=instruction_id,
                        status=authorization_status,
                    )
                )
        except OqiRemediationError as exc:
            self.session.rollback()
            raise ProductionRemediationOrchestrationError(exc.code) from exc
        self.session.commit()

        return PrepareRemediationResult(
            correlation_id=correlation_id,
            case_id=case.case_id,
            finding_id=finding_id,
            case_status=case.status.value,
            candidates=tuple(
                CandidateView(
                    candidate_id=c.candidate_id,
                    proposed_value=c.proposed_value,
                    basis=c.basis.value,
                )
                for c in candidates
            ),
            instructions=tuple(instruction_views),
            authorizations=tuple(authorization_views),
        )

    def _resolve_finding(
        self, *, tenant_id: str, finding_id: UUID
    ) -> tuple[RemediationFindingFamily, str | None] | None:
        """Read-only resolution of a bare `finding_id` to its governed
        remediation family (and, for OQI1-storage-shaped Findings, the
        semantic quality dimension `extract_candidates` needs to
        distinguish Completeness/Validity from Accuracy/Conformity, all
        three of which share `QualityFindingORM`'s own storage shape --
        CDD-058 SS3). Mirrors `OqiProductExperienceService`'s own private
        `_resolve_finding` probe pattern exactly, reimplemented here
        (rather than importing that unrelated read-service class) since
        CDD-058 authorizes no path in that file."""
        quality_model = self.session.get(QualityFindingORM, finding_id)
        if quality_model is not None and quality_model.tenant_id == tenant_id:
            dimension = self.session.execute(
                select(QualityRuleORM.dimension).where(
                    QualityRuleORM.quality_condition_id == quality_model.quality_condition_id,
                    QualityRuleORM.status == "ACTIVE",
                )
            ).scalar_one_or_none()
            if dimension == _ACCURACY_QUALITY_DIMENSION:
                return RemediationFindingFamily.OQI1, _ACCURACY_QUALITY_DIMENSION
            if dimension == _CONFORMITY_QUALITY_DIMENSION:
                return RemediationFindingFamily.OQI1, _CONFORMITY_QUALITY_DIMENSION
            return RemediationFindingFamily.OQI1, None

        comparison_model = self.session.get(QualityComparisonFindingORM, finding_id)
        if comparison_model is not None and comparison_model.tenant_id == tenant_id:
            return RemediationFindingFamily.OQI2, None

        rule_model = self.session.get(BusinessRuleFindingORM, finding_id)
        if rule_model is not None and rule_model.tenant_id == tenant_id:
            return RemediationFindingFamily.OQI3, None

        return None

    # ------------------------------------------------------------------
    # Remediation-scoped reevaluation (CDD-058 SS9/SS13/SS19-SS23),
    # invoked by the router immediately after its own existing, unmodified
    # `report_external_execution` call has already committed successfully.
    # ------------------------------------------------------------------

    def reevaluate_after_execution(
        self, *, tenant_id: str, authorization_id: UUID
    ) -> ReevaluationResult | None:
        repository = OqiRemediationRepositoryImpl(self.session)
        authorization = repository.get_authorization_by_id(authorization_id)
        if authorization is None or authorization.tenant_id != tenant_id:
            return None
        instruction = repository.get_instruction(authorization.instruction_id)
        if instruction is None:
            return None
        case = repository.get_case_by_id(instruction.case_id)
        if case is None:
            return None

        dq_result = self._reevaluate_dimension(
            tenant_id=tenant_id, case_finding_id=case.finding_id, finding_family=case.finding_family
        )

        ontology_impact_service = OqiOntologyImpactEvaluationService(
            OqiOntologyImpactEvaluationRepositoryImpl(self.session), clock=self._clock
        )
        ontology_impact = OntologyImpactReevaluationResult(status="NOT_ATTEMPTED")
        try:
            impact_evaluation = ontology_impact_service.evaluate_current_state(
                tenant_id=tenant_id,
                finding_family=OntologyImpactFindingFamily(case.finding_family.value),
                finding_id=case.finding_id,
            )
            self.session.commit()
        except Exception:  # noqa: BLE001 -- reported as FAILED, never NOT_EVALUABLE
            self.session.rollback()
            ontology_impact = OntologyImpactReevaluationResult(status="FAILED")
        else:
            if impact_evaluation is not None:
                ontology_impact = OntologyImpactReevaluationResult(
                    status="EVALUATED", outcome=impact_evaluation.outcome.value
                )

        business_impact_results: list[BusinessImpactReevaluationResult] = []
        reliance_result = RelianceReevaluationResult(status="NOT_ATTEMPTED")
        enterprise_entity_id = self._resolve_enterprise_entity_id(
            tenant_id=tenant_id, source_object_id=instruction.target_source_object_id
        )
        horizon = self._clock()
        if enterprise_entity_id is not None:
            try:
                business_impact_repo = OqiBusinessImpactRepositoryImpl(self.session)
                business_impact_service = OqiBusinessImpactService(self.session)
                dependencies = business_impact_repo.list_active_dependencies_for_subject(
                    tenant_id=tenant_id,
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=enterprise_entity_id,
                )
                computed_business_impact: list[BusinessImpactReevaluationResult] = []
                for dependency in dependencies:
                    impact = business_impact_service.evaluate_business_impact_for_dependency(
                        tenant_id=tenant_id,
                        dependency_id=dependency.dependency_id,
                        evaluated_at=horizon,
                    )
                    computed_business_impact.append(
                        BusinessImpactReevaluationResult(
                            dependency_id=dependency.dependency_id,
                            status="EVALUATED",
                            outcome=impact.outcome.value,
                        )
                    )
                reliance_evaluation = business_impact_service.evaluate_reliance_for_subject(
                    tenant_id=tenant_id,
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=enterprise_entity_id,
                    evaluated_at=horizon,
                )
                self.session.commit()
                business_impact_results = computed_business_impact
                reliance_result = RelianceReevaluationResult(
                    status="EVALUATED", state=reliance_evaluation.state.value
                )
            except Exception:  # noqa: BLE001 -- reported honestly, never NOT_EVALUABLE
                self.session.rollback()
                business_impact_results = []
                reliance_result = RelianceReevaluationResult(status="FAILED")

        finding_status_is_resolved = self._is_finding_resolved(
            tenant_id=tenant_id, finding_family=case.finding_family, finding_id=case.finding_id
        )
        remediation_service = OqiRemediationService(
            repository=repository,
            participant_reader=OqiRemediationParticipantReader(self.session),
        )
        try:
            refreshed_case = (
                remediation_service.refresh_case(
                    tenant_id=tenant_id,
                    finding_family=case.finding_family,
                    finding_id=case.finding_id,
                    now=self._clock(),
                )
                if finding_status_is_resolved
                else case
            )
            if finding_status_is_resolved:
                self.session.commit()
        except OqiRemediationError:
            self.session.rollback()
            refreshed_case = case

        return ReevaluationResult(
            case_id=case.case_id,
            finding_id=case.finding_id,
            case_status=refreshed_case.status.value,
            dq=dq_result,
            ontology_impact=ontology_impact,
            business_impact=tuple(business_impact_results),
            reliance=reliance_result,
        )

    def _reevaluate_dimension(
        self,
        *,
        tenant_id: str,
        case_finding_id: UUID,
        finding_family: RemediationFindingFamily,
    ) -> DqReevaluationResult:
        try:
            if finding_family is RemediationFindingFamily.OQI2:
                comparison_model = self.session.get(QualityComparisonFindingORM, case_finding_id)
                if comparison_model is None or comparison_model.tenant_id != tenant_id:
                    return DqReevaluationResult(status="NOT_EVALUABLE")
                consistency_rule = OqiQualityRuleRepositoryImpl(self.session).get_active(
                    comparison_model.quality_condition_id
                )
                correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(
                    self.session
                ).get_active(
                    tenant_id=tenant_id,
                    comparison_subject_id=comparison_model.comparison_subject_id,
                )
                if consistency_rule is None or correspondence is None:
                    return DqReevaluationResult(status="NOT_EVALUABLE")
                consistency_evaluation = OqiCrossSourceEvaluationService(
                    evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(self.session),
                    clock=self._clock,
                ).evaluate_current_state(rule=consistency_rule, correspondence=correspondence)
                self.session.commit()
                if consistency_evaluation is None:
                    return DqReevaluationResult(status="NOT_EVALUABLE")
                return DqReevaluationResult(
                    status="EVALUATED", outcome=consistency_evaluation.outcome.value
                )

            # ACCURACY/CONFORMITY only -- OQI1 (Completeness/Validity) and
            # OQI3 (Reasonableness) never generate a real candidate
            # (CDD-058 SS12), so remediation-scoped reevaluation is only
            # ever reached for a Finding whose case originated from a real
            # candidate, i.e. OQI2/Accuracy/Conformity.
            finding_model = self.session.get(QualityFindingORM, case_finding_id)
            if finding_model is None or finding_model.tenant_id != tenant_id:
                return DqReevaluationResult(status="NOT_EVALUABLE")
            quality_rule = OqiQualityRuleRepositoryImpl(self.session).get_active(
                finding_model.quality_condition_id
            )
            if quality_rule is None:
                return DqReevaluationResult(status="NOT_EVALUABLE")
            subject = EvaluationSubject(
                lineage=SourceRecordLineageIdentity(
                    tenant_id=tenant_id,
                    source_object_id=finding_model.source_object_id,
                    source_record_reference=finding_model.source_record_reference,
                ),
                source_field_id=finding_model.source_field_id,
            )
            if quality_rule.dimension is QualityDimension.ACCURACY:
                accuracy_evaluation = OqiAccuracyEvaluationService(
                    evaluation_repository=OqiAccuracyEvaluationRepositoryImpl(self.session),
                    reference_evidence_lookup=OqiReferenceEvidenceService(
                        repository=OqiReferenceEvidenceRepositoryImpl(self.session),
                        clock=self._clock,
                    ),
                    clock=self._clock,
                ).evaluate_current_state(rule=quality_rule, subject=subject)
                self.session.commit()
                if accuracy_evaluation is None:
                    return DqReevaluationResult(status="NOT_EVALUABLE")
                return DqReevaluationResult(
                    status="EVALUATED", outcome=accuracy_evaluation.outcome.value
                )
            if quality_rule.dimension is QualityDimension.CONFORMITY:
                conformity_evaluation = OqiConformityEvaluationService(
                    evaluation_repository=OqiConformityEvaluationRepositoryImpl(self.session),
                    canonical_standard_lookup=OqiCanonicalStandardRepositoryImpl(self.session),
                    clock=self._clock,
                ).evaluate_current_state(rule=quality_rule, subject=subject)
                self.session.commit()
                if conformity_evaluation is None:
                    return DqReevaluationResult(status="NOT_EVALUABLE")
                return DqReevaluationResult(
                    status="EVALUATED", outcome=conformity_evaluation.outcome.value
                )
            return DqReevaluationResult(status="NOT_EVALUABLE")
        except Exception:  # noqa: BLE001 -- reported FAILED, never NOT_EVALUABLE
            self.session.rollback()
            return DqReevaluationResult(status="FAILED")

    def _is_finding_resolved(
        self, *, tenant_id: str, finding_family: RemediationFindingFamily, finding_id: UUID
    ) -> bool:
        repository = OqiRemediationRepositoryImpl(self.session)
        if finding_family is RemediationFindingFamily.OQI1:
            state = repository.get_oqi1_finding_state(tenant_id=tenant_id, finding_id=finding_id)
        elif finding_family is RemediationFindingFamily.OQI2:
            state = repository.get_oqi2_finding_state(tenant_id=tenant_id, finding_id=finding_id)
        else:
            state = repository.get_oqi3_finding_state(tenant_id=tenant_id, finding_id=finding_id)
        return state is not None and state.status == "RESOLVED"

    def _resolve_enterprise_entity_id(
        self, *, tenant_id: str, source_object_id: UUID
    ) -> UUID | None:
        store = EntityResolutionStore(self.session)
        key = store.understanding_key((source_object_id,))
        record = store.get_current_record(tenant_id, key)
        if record is None:
            return None
        return record.enterprise_entity_id
