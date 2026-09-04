"""Production OQI Explicit Evaluation Orchestration (CDD-056). Composes the
nine already-existing, already-verified governed DQ dimension evaluators,
OQI4 Ontology Impact, OQI6 Business Impact, and Reliance in their existing
dependency order. This module introduces zero new domain/authority logic --
every evaluation decision is made by an existing, unmodified evaluator; this
file only performs read-only lookups against already-persisted governed
configuration (semantic mappings, quality rules, business-rule bindings,
canonical standards, reference evidence, relationship requirements,
timeliness policies, entity resolution, business dependencies) to determine
which already-existing evaluators are applicable for the requested subject,
then sequences calls to them exactly as CDD-056 SS14-SS19 freezes.

Absence of a governed prerequisite (no active rule/policy/correspondence/
relationship-requirement/entity-resolution) is reported as NOT_EVALUABLE,
never fabricated, never treated as a technical failure (CDD-056 SS12,
SS21-SS23). No dimension's own evaluator is modified; every read here uses
`select(...)` (never a `ClassName(...)` construction), so no ORM class's
single-construction-site invariant (`test_runtime_architecture.py`) is
affected by this file.

`FindingFamily` (CDD-042 SS10) is closed to exactly OQI1/OQI2/OQI3 -- H4
Integrity and H5 Timeliness Findings are never OQI4 inputs; only
Completeness/Validity/Accuracy/Conformity (all OQI1-storage-shaped) and
Reasonableness (OQI3) and Consistency (OQI2) evaluations feed OQI4.

Tenant authority is a required keyword argument on every public method here
-- callers (the API layer) must source it exclusively from
`TrustedPrincipal.tenant_id`, never from request-body content (CDD-056
SS6)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.oqi_accuracy_evaluation_service import OqiAccuracyEvaluationService
from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_business_rule_evaluation_service import (
    OqiBusinessRuleEvaluationService,
    SingleRecordSubject,
)
from app.application.oqi_conformity_evaluation_service import OqiConformityEvaluationService
from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.application.oqi_integrity_reference_evaluation_service import (
    OqiIntegrityReferenceEvaluationService,
)
from app.application.oqi_integrity_structural_evaluation_service import (
    OqiIntegrityStructuralEvaluationService,
)
from app.application.oqi_ontology_impact_evaluation_service import (
    OqiOntologyImpactEvaluationService,
)
from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
from app.application.oqi_reference_evidence_service import OqiReferenceEvidenceService
from app.application.oqi_timeliness_evaluation_service import OqiTimelinessEvaluationService
from app.domain.oqi.evaluation import (
    EvaluationSubject,
    SourceRecordLineageIdentity,
    canonical_subject_identity,
    derive_quality_finding_id,
)
from app.domain.oqi.quality_rule import QualityDimension, QualityRule, QualityRuleStatus
from app.domain.oqi_business_rule.finding import derive_business_rule_finding_id
from app.domain.oqi_business_rule.rule import BusinessRule
from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
from app.domain.oqi_ontology_impact.evaluation import FindingFamily, OntologyElementType
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.oqi_business_rule import (
    BusinessRuleInputBindingORM,
    BusinessRuleORM,
)
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM
from app.infrastructure.persistence.oqi_accuracy_evaluation_repository import (
    OqiAccuracyEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)
from app.infrastructure.persistence.oqi_business_rule_evaluation_repository import (
    OqiBusinessRuleEvaluationRepositoryImpl,
    OqiBusinessRuleEvidenceValueReader,
)
from app.infrastructure.persistence.oqi_business_rule_repository import (
    OqiBusinessRuleRepositoryImpl,
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
from app.infrastructure.persistence.oqi_integrity_reference_evaluation_repository import (
    OqiIntegrityReferenceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_integrity_requirement_repository import (
    OqiIntegrityRequirementRepositoryImpl,
)
from app.infrastructure.persistence.oqi_integrity_structural_evaluation_repository import (
    OqiIntegrityStructuralEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import (
    OqiQualityRuleRepositoryImpl,
)
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_timeliness_evaluation_repository import (
    OqiTimelinessEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_timeliness_policy_repository import (
    OqiTimelinessPolicyRepositoryImpl,
)
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepository,
    SemanticMappingRepositoryImpl,
)


@dataclass(frozen=True, slots=True)
class DimensionResult:
    dimension: str
    status: str  # "EVALUATED" | "NOT_EVALUABLE" | "FAILED"
    evaluation_id: UUID | None = None
    outcome: str | None = None


@dataclass(frozen=True, slots=True)
class OntologyImpactResult:
    status: str  # "EVALUATED" | "NOT_ATTEMPTED" | "FAILED"
    outcome: str | None = None


@dataclass(frozen=True, slots=True)
class BusinessImpactResult:
    dependency_id: UUID
    status: str
    outcome: str | None = None


@dataclass(frozen=True, slots=True)
class RelianceResult:
    status: str
    state: str | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    correlation_id: UUID | None
    evaluated_at: datetime
    dimensions: tuple[DimensionResult, ...]
    ontology_impact: OntologyImpactResult
    business_impact: tuple[BusinessImpactResult, ...] = field(default_factory=tuple)
    reliance: RelianceResult = field(default_factory=lambda: RelianceResult(status="NOT_ATTEMPTED"))


class OqiEvaluationOrchestrationService:
    """CDD-056: composition-only orchestrator. Owns no persistence of its
    own; every write happens through an existing, unmodified evaluator's own
    existing transaction boundary."""

    def __init__(
        self, session: Session, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self.session = session
        self._clock = clock

    # ------------------------------------------------------------------
    # Read-only prerequisite resolution (CDD-056 SS12). No ORM class is
    # constructed here -- every lookup is a `select(...)`.
    # ------------------------------------------------------------------

    def _resolve_semantic_mapping(
        self, *, tenant_id: str, information_element_requirement_id: UUID
    ) -> object | None:
        repo: SemanticMappingRepository = SemanticMappingRepositoryImpl(self.session)
        return repo.get_approved_by_information_element_requirement(
            information_element_requirement_id, tenant_id
        )

    def _resolve_active_quality_rule(
        self, *, information_element_requirement_id: UUID, dimension: QualityDimension
    ) -> QualityRule | None:
        rule_id = self.session.execute(
            select(QualityRuleORM.rule_id).where(
                QualityRuleORM.information_element_requirement_id
                == str(information_element_requirement_id),
                QualityRuleORM.dimension == dimension.value,
                QualityRuleORM.status == QualityRuleStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        if rule_id is None:
            return None
        return OqiQualityRuleRepositoryImpl(self.session).get_by_id(rule_id)

    def _resolve_active_business_rule(
        self, *, tenant_id: str, source_field_id: UUID
    ) -> BusinessRule | None:
        rule_id = self.session.execute(
            select(BusinessRuleORM.rule_id)
            .join(
                BusinessRuleInputBindingORM,
                BusinessRuleInputBindingORM.rule_id == BusinessRuleORM.rule_id,
            )
            .where(
                BusinessRuleInputBindingORM.source_field_id == source_field_id,
                BusinessRuleORM.tenant_id == tenant_id,
                BusinessRuleORM.status == "ACTIVE",
            )
        ).scalar_one_or_none()
        if rule_id is None:
            return None
        return OqiBusinessRuleRepositoryImpl(self.session).get_by_id(rule_id)

    def _resolve_relationship_requirement_id(
        self, *, information_element_requirement_id: UUID
    ) -> UUID | None:
        """CDD-056 SS12/SS18: `InformationElementRequirement` and
        `RelationshipRequirement` share a common `concept_requirement_id` --
        the only already-governed relational path from the requested
        subject to a candidate H4 requirement. Absence -> NOT_EVALUABLE for
        both Integrity sub-dimensions, never fabricated."""
        from app.infrastructure.persistence.models.blueprint import (
            InformationElementRequirementORM,
            RelationshipRequirementORM,
        )

        concept_requirement_id = self.session.execute(
            select(InformationElementRequirementORM.concept_requirement_id).where(
                InformationElementRequirementORM.information_element_requirement_id
                == information_element_requirement_id
            )
        ).scalar_one_or_none()
        if concept_requirement_id is None:
            return None
        return self.session.execute(
            select(RelationshipRequirementORM.relationship_requirement_id)
            .where(RelationshipRequirementORM.concept_requirement_id == concept_requirement_id)
            .limit(1)
        ).scalar_one_or_none()

    def _resolve_enterprise_entity_id(
        self, *, tenant_id: str, source_object_id: UUID
    ) -> UUID | None:
        store = EntityResolutionStore(self.session)
        key = store.understanding_key((source_object_id,))
        record = store.get_current_record(tenant_id, key)
        if record is None:
            return None
        return record.enterprise_entity_id

    # ------------------------------------------------------------------
    # Public orchestration entry point.
    # ------------------------------------------------------------------

    def evaluate(
        self,
        *,
        tenant_id: str,
        information_element_requirement_id: UUID,
        source_record_reference: str,
        business_process_id: UUID,
        business_process_version: int,
        correlation_id: UUID | None = None,
    ) -> OrchestrationResult:
        horizon = self._clock()
        dimension_results: list[DimensionResult] = []
        finding_refs: list[tuple[FindingFamily, UUID]] = []

        mapping = self._resolve_semantic_mapping(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
        )
        source_field_id: UUID | None = mapping.source_field_id if mapping is not None else None  # type: ignore[attr-defined]
        source_object_id: UUID | None = mapping.source_object_id if mapping is not None else None  # type: ignore[attr-defined]
        subject: EvaluationSubject | None = (
            EvaluationSubject(
                lineage=SourceRecordLineageIdentity(
                    tenant_id=tenant_id,
                    source_object_id=source_object_id,
                    source_record_reference=source_record_reference,
                ),
                source_field_id=source_field_id,
            )
            if source_field_id is not None and source_object_id is not None
            else None
        )

        # --- 1/2. COMPLETENESS + VALIDITY (OQI1) ---
        quality_repo = OqiQualityEvaluationRepositoryImpl(self.session)
        quality_service = OqiQualityEvaluationService(
            evaluation_repository=quality_repo,
            clock=self._clock,
        )
        for dim in (QualityDimension.COMPLETENESS, QualityDimension.VALIDITY):
            rule = (
                self._resolve_active_quality_rule(
                    information_element_requirement_id=information_element_requirement_id,
                    dimension=dim,
                )
                if subject is not None
                else None
            )
            if rule is None or subject is None:
                dimension_results.append(DimensionResult(dim.value, "NOT_EVALUABLE"))
                continue
            oqi1_evaluation = quality_service.evaluate_current_state(rule=rule, subject=subject)
            if oqi1_evaluation is None:
                dimension_results.append(DimensionResult(dim.value, "NOT_EVALUABLE"))
                continue
            dimension_results.append(
                DimensionResult(
                    dim.value,
                    "EVALUATED",
                    oqi1_evaluation.evaluation_id,
                    oqi1_evaluation.outcome.value,
                )
            )
            finding_id = derive_quality_finding_id(
                tenant_id=tenant_id,
                quality_condition_id=oqi1_evaluation.quality_condition_id,
                subject_type=subject.subject_type,
                subject_identity=canonical_subject_identity(subject),
            )
            # A SATISFIED outcome with no pre-existing Finding never creates
            # one (CDD-039 SS23-25) -- only feed OQI4 a Finding that genuinely
            # persisted.
            if quality_repo.get_finding(finding_id) is not None:
                finding_refs.append((FindingFamily.OQI1, finding_id))

        # --- 3. ACCURACY ---
        accuracy_rule = (
            self._resolve_active_quality_rule(
                information_element_requirement_id=information_element_requirement_id,
                dimension=QualityDimension.ACCURACY,
            )
            if subject is not None
            else None
        )
        if accuracy_rule is None or subject is None:
            dimension_results.append(
                DimensionResult(QualityDimension.ACCURACY.value, "NOT_EVALUABLE")
            )
        else:
            accuracy_repo = OqiAccuracyEvaluationRepositoryImpl(self.session)
            accuracy_service = OqiAccuracyEvaluationService(
                evaluation_repository=accuracy_repo,
                reference_evidence_lookup=OqiReferenceEvidenceService(
                    repository=OqiReferenceEvidenceRepositoryImpl(self.session), clock=self._clock
                ),
                clock=self._clock,
            )
            accuracy_evaluation = accuracy_service.evaluate_current_state(
                rule=accuracy_rule, subject=subject
            )
            if accuracy_evaluation is None:
                dimension_results.append(
                    DimensionResult(QualityDimension.ACCURACY.value, "NOT_EVALUABLE")
                )
            else:
                dimension_results.append(
                    DimensionResult(
                        QualityDimension.ACCURACY.value,
                        "EVALUATED",
                        accuracy_evaluation.evaluation_id,
                        accuracy_evaluation.outcome.value,
                    )
                )
                accuracy_finding_id = derive_quality_finding_id(
                    tenant_id=tenant_id,
                    quality_condition_id=accuracy_evaluation.quality_condition_id,
                    subject_type=subject.subject_type,
                    subject_identity=canonical_subject_identity(subject),
                )
                if accuracy_repo.get_finding(accuracy_finding_id) is not None:
                    finding_refs.append((FindingFamily.OQI1, accuracy_finding_id))

        # --- 5. REASONABLENESS (OQI3) ---
        business_rule = (
            self._resolve_active_business_rule(tenant_id=tenant_id, source_field_id=source_field_id)
            if source_field_id is not None
            else None
        )
        if business_rule is None or source_object_id is None:
            dimension_results.append(DimensionResult("REASONABLENESS", "NOT_EVALUABLE"))
        else:
            reasonableness_repo = OqiBusinessRuleEvaluationRepositoryImpl(self.session)
            reasonableness_service = OqiBusinessRuleEvaluationService(
                evaluation_repository=reasonableness_repo,
                evidence_value_reader=OqiBusinessRuleEvidenceValueReader(self.session),
                clock=self._clock,
            )
            single_subject = SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference=source_record_reference,
            )
            business_rule_evaluation = reasonableness_service.evaluate_current_state(
                rule=business_rule, subject=single_subject
            )
            if business_rule_evaluation is None:
                dimension_results.append(DimensionResult("REASONABLENESS", "NOT_EVALUABLE"))
            else:
                dimension_results.append(
                    DimensionResult(
                        "REASONABLENESS",
                        "EVALUATED",
                        business_rule_evaluation.evaluation_id,
                        business_rule_evaluation.outcome.value,
                    )
                )
                reasonableness_finding_id = derive_business_rule_finding_id(
                    tenant_id=tenant_id,
                    business_condition_id=business_rule_evaluation.business_condition_id,
                    subject_type=business_rule_evaluation.subject_type,
                    subject_identity=business_rule_evaluation.subject_identity,
                )
                if reasonableness_repo.get_finding(reasonableness_finding_id) is not None:
                    finding_refs.append((FindingFamily.OQI3, reasonableness_finding_id))

        # --- 6. CONFORMITY ---
        conformity_rule = (
            self._resolve_active_quality_rule(
                information_element_requirement_id=information_element_requirement_id,
                dimension=QualityDimension.CONFORMITY,
            )
            if subject is not None
            else None
        )
        if conformity_rule is None or subject is None:
            dimension_results.append(
                DimensionResult(QualityDimension.CONFORMITY.value, "NOT_EVALUABLE")
            )
        else:
            conformity_repo = OqiConformityEvaluationRepositoryImpl(self.session)
            conformity_service = OqiConformityEvaluationService(
                evaluation_repository=conformity_repo,
                canonical_standard_lookup=OqiCanonicalStandardRepositoryImpl(self.session),
                clock=self._clock,
            )
            conformity_evaluation = conformity_service.evaluate_current_state(
                rule=conformity_rule, subject=subject
            )
            if conformity_evaluation is None:
                dimension_results.append(
                    DimensionResult(QualityDimension.CONFORMITY.value, "NOT_EVALUABLE")
                )
            else:
                dimension_results.append(
                    DimensionResult(
                        QualityDimension.CONFORMITY.value,
                        "EVALUATED",
                        conformity_evaluation.evaluation_id,
                        conformity_evaluation.outcome.value,
                    )
                )
                conformity_finding_id = derive_quality_finding_id(
                    tenant_id=tenant_id,
                    quality_condition_id=conformity_evaluation.quality_condition_id,
                    subject_type=subject.subject_type,
                    subject_identity=canonical_subject_identity(subject),
                )
                if conformity_repo.get_finding(conformity_finding_id) is not None:
                    finding_refs.append((FindingFamily.OQI1, conformity_finding_id))

        # --- 4. CONSISTENCY (OQI2) --- comparison_subject_id resolved by
        # this orchestrator's own documented convention: the same UUID
        # value as information_element_requirement_id, reused as the
        # correspondence's comparison_subject_id. No governed data links
        # these two identifier spaces automatically (confirmed during
        # implementation); absence of a correspondence configured under
        # this convention is a legitimate NOT_EVALUABLE, per CDD-056 SS12.
        consistency_rule = self._resolve_active_quality_rule(
            information_element_requirement_id=information_element_requirement_id,
            dimension=QualityDimension.CONSISTENCY,
        )
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(self.session).get_active(
            tenant_id=tenant_id, comparison_subject_id=information_element_requirement_id
        )
        if consistency_rule is None or correspondence is None:
            dimension_results.append(
                DimensionResult(QualityDimension.CONSISTENCY.value, "NOT_EVALUABLE")
            )
        else:
            consistency_repo = OqiCrossSourceEvaluationRepositoryImpl(self.session)
            cross_source_service = OqiCrossSourceEvaluationService(
                evaluation_repository=consistency_repo,
                clock=self._clock,
            )
            consistency_evaluation = cross_source_service.evaluate_current_state(
                rule=consistency_rule, correspondence=correspondence
            )
            if consistency_evaluation is None:
                dimension_results.append(
                    DimensionResult(QualityDimension.CONSISTENCY.value, "NOT_EVALUABLE")
                )
            else:
                dimension_results.append(
                    DimensionResult(
                        QualityDimension.CONSISTENCY.value,
                        "EVALUATED",
                        consistency_evaluation.evaluation_id,
                        consistency_evaluation.outcome.value,
                    )
                )
                consistency_finding_id = derive_comparison_finding_id(
                    tenant_id=tenant_id,
                    quality_condition_id=consistency_evaluation.quality_condition_id,
                    comparison_subject_id=consistency_evaluation.comparison_subject_id,
                )
                if consistency_repo.get_finding(consistency_finding_id) is not None:
                    finding_refs.append((FindingFamily.OQI2, consistency_finding_id))

        # --- 7/8. INTEGRITY STRUCTURAL / REFERENCE (never OQI4 inputs --
        # FindingFamily is closed to OQI1/OQI2/OQI3, CDD-042 SS10) ---
        relationship_requirement_id = self._resolve_relationship_requirement_id(
            information_element_requirement_id=information_element_requirement_id
        )
        enterprise_entity_id = (
            self._resolve_enterprise_entity_id(
                tenant_id=tenant_id, source_object_id=source_object_id
            )
            if source_object_id is not None
            else None
        )
        if relationship_requirement_id is None or enterprise_entity_id is None:
            dimension_results.append(DimensionResult("INTEGRITY_STRUCTURAL", "NOT_EVALUABLE"))
        else:
            structural_service = OqiIntegrityStructuralEvaluationService(
                evaluation_repository=OqiIntegrityStructuralEvaluationRepositoryImpl(self.session),
                cardinality_lookup=OqiIntegrityRequirementRepositoryImpl(self.session),
                clock=self._clock,
            )
            structural_evaluation = structural_service.evaluate_current_state(
                tenant_id=tenant_id,
                enterprise_entity_id=enterprise_entity_id,
                relationship_requirement_id=relationship_requirement_id,
            )
            if structural_evaluation is None:
                dimension_results.append(DimensionResult("INTEGRITY_STRUCTURAL", "NOT_EVALUABLE"))
            else:
                dimension_results.append(
                    DimensionResult(
                        "INTEGRITY_STRUCTURAL",
                        "EVALUATED",
                        structural_evaluation.evaluation_id,
                        structural_evaluation.outcome.value,
                    )
                )

        if relationship_requirement_id is None or source_object_id is None:
            dimension_results.append(DimensionResult("INTEGRITY_REFERENCE", "NOT_EVALUABLE"))
        else:
            reference_service = OqiIntegrityReferenceEvaluationService(
                evaluation_repository=OqiIntegrityReferenceEvaluationRepositoryImpl(self.session),
                clock=self._clock,
            )
            reference_evaluation = reference_service.evaluate_current_state(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                relationship_requirement_id=relationship_requirement_id,
            )
            if reference_evaluation is None:
                dimension_results.append(DimensionResult("INTEGRITY_REFERENCE", "NOT_EVALUABLE"))
            else:
                dimension_results.append(
                    DimensionResult(
                        "INTEGRITY_REFERENCE",
                        "EVALUATED",
                        reference_evaluation.evaluation_id,
                        reference_evaluation.outcome.value,
                    )
                )

        # --- 9. TIMELINESS (never an OQI4 input, same closed-family reason) ---
        timeliness_repo = OqiTimelinessEvaluationRepositoryImpl(self.session)
        timeliness_service = OqiTimelinessEvaluationService(
            evaluation_repository=timeliness_repo,
            evidence_lookup=timeliness_repo,
            policy_lookup=OqiTimelinessPolicyRepositoryImpl(self.session),
            semantic_mapping_lookup=SemanticMappingRepositoryImpl(self.session),
            clock=self._clock,
        )
        timeliness_results = timeliness_service.evaluate_current_state(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            business_process_id=business_process_id,
            business_process_version=business_process_version,
            evaluation_horizon=horizon,
        )
        if not timeliness_results:
            dimension_results.append(DimensionResult("TIMELINESS", "NOT_EVALUABLE"))
        else:
            for timeliness_evaluation in timeliness_results:
                dimension_results.append(
                    DimensionResult(
                        "TIMELINESS",
                        "EVALUATED",
                        timeliness_evaluation.evaluation_id,
                        timeliness_evaluation.outcome.value,
                    )
                )

        # --- OQI4 Ontology Impact: one evaluation per collected finding ref ---
        ontology_impact_service = OqiOntologyImpactEvaluationService(
            OqiOntologyImpactEvaluationRepositoryImpl(self.session), clock=self._clock
        )
        ontology_impact = OntologyImpactResult(status="NOT_ATTEMPTED")
        for finding_family, finding_id in finding_refs:
            try:
                impact_evaluation = ontology_impact_service.evaluate_current_state(
                    tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
                )
            except Exception:  # noqa: BLE001 -- reported as FAILED, never NOT_EVALUABLE
                ontology_impact = OntologyImpactResult(status="FAILED")
                continue
            if impact_evaluation is not None:
                ontology_impact = OntologyImpactResult(
                    status="EVALUATED", outcome=impact_evaluation.outcome.value
                )

        # --- OQI6 Business Impact + Reliance ---
        business_impact_results: list[BusinessImpactResult] = []
        reliance_result = RelianceResult(status="NOT_ATTEMPTED")
        if enterprise_entity_id is not None:
            business_impact_repo = OqiBusinessImpactRepositoryImpl(self.session)
            business_impact_service = OqiBusinessImpactService(self.session)
            dependencies = business_impact_repo.list_active_dependencies_for_subject(
                tenant_id=tenant_id,
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=enterprise_entity_id,
            )
            for dependency in dependencies:
                try:
                    impact = business_impact_service.evaluate_business_impact_for_dependency(
                        tenant_id=tenant_id,
                        dependency_id=dependency.dependency_id,
                        evaluated_at=horizon,
                    )
                    business_impact_results.append(
                        BusinessImpactResult(
                            dependency_id=dependency.dependency_id,
                            status="EVALUATED",
                            outcome=impact.outcome.value,
                        )
                    )
                except Exception:  # noqa: BLE001 -- reported honestly, never NOT_EVALUABLE
                    business_impact_results.append(
                        BusinessImpactResult(
                            dependency_id=dependency.dependency_id, status="FAILED"
                        )
                    )
            try:
                reliance_evaluation = business_impact_service.evaluate_reliance_for_subject(
                    tenant_id=tenant_id,
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=enterprise_entity_id,
                    evaluated_at=horizon,
                )
                reliance_result = RelianceResult(
                    status="EVALUATED", state=reliance_evaluation.state.value
                )
            except Exception:  # noqa: BLE001
                reliance_result = RelianceResult(status="FAILED")

        return OrchestrationResult(
            correlation_id=correlation_id,
            evaluated_at=horizon,
            dimensions=tuple(dimension_results),
            ontology_impact=ontology_impact,
            business_impact=tuple(business_impact_results),
            reliance=reliance_result,
        )
