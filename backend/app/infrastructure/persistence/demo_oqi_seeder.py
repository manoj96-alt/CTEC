"""Deterministic, idempotent OQI demo-showcase seeder (Docker-I, governed by
the Docker-G freeze). Never invoked by normal production bootstrap --
`app.main`'s lifespan only ever builds the dependency Container; nothing on
the request path calls this module. Has its own, separate, manually-run CLI
entrypoint (see `__main__` below) and must be invoked deliberately --
following `demo_gate_f_seeder.py`'s exact precedent.

Refuses to seed any tenant other than the labeled demo tenant
(`BOOTSTRAP_DEMO_TENANT_ID`).

Seeds INPUT + CONTEXT only, never a directly-persisted OQI conclusion:

  - two source systems (SAP, PLM) and one field per system carrying a
    genuinely disagreeing "Country of Origin" observation for the same
    real-world supplier (SAP: "US", PLM: "MX") -- raw evidence, exactly the
    shape a real ingestion pipeline would admit. No repository wraps mere
    evidence admission (it is not a governed decision);
  - one governed, ACTIVE OQI2 cross-source `QualityRule` and
    `ComparisonSubjectCorrespondence` linking those two source fields --
    governed configuration, the rule/condition definition itself, the same
    class of artifact as an ontology entity/relationship type, never a
    conclusion;
  - one `EnterpriseEntity` (the demo Supplier) plus real entity-resolution
    records binding both source objects to it -- context, never a Finding;
  - one governed `BusinessProcess` ("Supplier Qualification (Demo)") and
    `BusinessDependency` (criticality HIGH) on that same entity -- again
    configuration, never a computed outcome.

Then, and only then, calls the REAL, unmodified production evaluators --
`OqiCrossSourceEvaluationService.evaluate_current_state` (OQI2),
`OqiOntologyImpactEvaluationService.evaluate_current_state` (OQI4), and
`OqiBusinessImpactService.evaluate_business_impact_for_dependency` /
`.evaluate_reliance_for_subject` (OQI6) -- so every Finding, ontology-impact
row, business-impact row, and Reliance state a fresh Docker demo shows is the
real, governed output of real evaluation logic applied to real seeded
evidence, never a directly-persisted conclusion.

No `RemediationAuthorization`, no external-execution report, and no Finding
resolution is ever seeded here. Agent investigation/recommendation (OQI5) is
also never seeded here. Those remain exclusively the live, interactive,
governed browser lifecycle the Docker demo actually exercises.

Idempotent: every id this module itself assigns is deterministic (`uuid5`,
namespaced under the existing `BOOTSTRAP_SEED_NAMESPACE`); the one-time
context setup is gated behind a single existence check (mirroring
`demo_gate_f_seeder.py`'s own gating discipline) and is skipped entirely on
a second run; the evaluation calls are re-run every invocation regardless,
since OQI2/OQI4/OQI6 each already idempotently dedupe on their own real
digest/ledger design -- re-running `seed()` against an already-seeded
database creates nothing new."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

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
from app.application.oqi_reference_evidence_service import OqiReferenceEvidenceService
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
)
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EnterpriseEntityResolutionRecord,
    ResolutionOutcome,
)
from app.domain.integration import SourceField
from app.domain.oqi.evaluation import EvaluationSubject, SourceRecordLineageIdentity
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_business_impact.dependency import Criticality
from app.domain.oqi_business_impact.process import BusinessImpactCategory
from app.domain.oqi_business_rule.rule import (
    BusinessRule,
    BusinessRuleInputBinding,
    BusinessRulePurpose,
    BusinessRuleStatus,
    ComparandKind,
    ComparatorNode,
    ExpectedType,
    Operator,
    RuleFamily,
)
from app.domain.oqi_canonical_standard.standard import (
    CanonicalAlias,
    CanonicalStandard,
    CanonicalStandardStatus,
    CanonicalValue,
)
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
from app.domain.oqi_integrity.requirement import (
    IntegrityRelationshipCardinality,
    IntegrityRelationshipCardinalityStatus,
)
from app.domain.oqi_ontology_impact.evaluation import FindingFamily, OntologyElementType
from app.domain.semantic_mapping.model import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.blueprint import RelationshipRequirementORM
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
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
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

SEED_TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)

_QUALITY_CONDITION_ID = "oqi-demo-supplier-country-of-origin"


def _uid(label: str) -> UUID:
    return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"oqi-demo:{label}")


_SAP_SYSTEM_ID = _uid("sap-system")
_PLM_SYSTEM_ID = _uid("plm-system")
_SAP_OBJECT_ID = _uid("sap-object")
_PLM_OBJECT_ID = _uid("plm-object")
_SAP_FIELD_ID = _uid("sap-field")
_PLM_FIELD_ID = _uid("plm-field")
_SUPPLIER_ENTITY_ID = _uid("supplier-entity")
_COMPARISON_SUBJECT_ID = _uid("comparison-subject")

# CDD-048 §30 (OQI-H2 demo crown scenario): reuses the exact SAP/PLM
# Country-of-Origin disagreement above -- SAP="US" (matches governed
# Reference Evidence), PLM="MX" (does not) -- deriving Accuracy from raw
# evidence + a governed Reference Evidence assertion, never a fabricated
# terminal Finding.
_ACCURACY_QUALITY_CONDITION_ID = "oqi-demo-supplier-country-accuracy"
_QUANTITY_FIELD_ID = _uid("sap-quantity-field")
_REASONABLENESS_BUSINESS_CONDITION_ID = "oqi-demo-order-quantity-reasonableness"

# CDD-049 §30 (OQI-H3 demo crown scenario; OQI-H3-I-R1 amendment §5-§6): a
# NEW, distinct field pair -- deliberately NOT reusing _SAP_FIELD_ID/
# _PLM_FIELD_ID (whose raw "US"/"MX" values remain exactly as H2 seeded
# them, unaffected by this addition). SAP="US" (a recognized non-canonical
# alias), PLM="USA" (the governed canonical form) -- on the SAME already-
# resolved SAP/PLM SourceObjects, so the existing entity resolution and
# BusinessDependency downstream chain applies without any new seeding.
_H3_SAP_FIELD_ID = _uid("h3-sap-manufacturing-country-field")
_H3_PLM_FIELD_ID = _uid("h3-plm-manufacturing-country-field")

# The genuine governed Information Element prerequisite chain (OQI-H3-I-R1
# amendment §5): a NEW, separately-named, Approved Blueprint -- never
# superseding or modifying the existing canonical
# "CTEC Semiconductor Supply Chain Blueprint" -- referencing the
# already-seeded "Supplier" EntityType (OntologySeeder, unmodified).
_H3_BLUEPRINT_ID = _uid("h3-demo-blueprint")
_H3_CONCEPT_REQUIREMENT_ID = _uid("h3-demo-concept-requirement")
_H3_INFORMATION_ELEMENT_REQUIREMENT_ID = _uid("h3-manufacturing-country-ie")
_H3_SAP_SEMANTIC_MAPPING_ID = _uid("h3-sap-semantic-mapping")
_H3_PLM_SEMANTIC_MAPPING_ID = _uid("h3-plm-semantic-mapping")
_H3_SUPPLIER_ENTITY_TYPE_NAME = "Supplier"

# Governed CanonicalStandard: canonical "USA", recognized alias "US".
_H3_CANONICAL_STANDARD_ID = _uid("h3-canonical-standard-manufacturing-country-v1")
_H3_CANONICAL_VALUE_ID = _uid("h3-canonical-value-usa")
_H3_CANONICAL_ALIAS_ID = _uid("h3-canonical-alias-us")

# Two Conformity QualityRules (one per source field) plus one Consistency
# QualityRule/ComparisonSubjectCorrespondence pair -- all three sharing
# _H3_INFORMATION_ELEMENT_REQUIREMENT_ID (PO-H3-01: the same governed
# Information Element anchors both).
_H3_SAP_CONFORMITY_CONDITION_ID = "oqi-demo-h3-sap-manufacturing-country-conformity"
_H3_PLM_CONFORMITY_CONDITION_ID = "oqi-demo-h3-plm-manufacturing-country-conformity"
_H3_CONSISTENCY_CONDITION_ID = "oqi-demo-h3-manufacturing-country-consistency"
_H3_COMPARISON_SUBJECT_ID = _uid("h3-comparison-subject")

# CDD-050 §28 (OQI-H4 demo crown scenario): the ALREADY-GOVERNED, real
# `assembledAt` RelationshipRequirement (Product -> Facility, REQUIRED) --
# zero new Blueprint/ConceptRequirement/RelationshipRequirement. One new
# ACTIVE IntegrityRelationshipCardinality (min=1, max=1) anchors it. Three
# new EnterpriseEntity trios (scenarios A/B/C) plus one new SourceObject
# with a genuine ResolutionOutcome.UNRESOLVED record (scenario D).
_H4_ASSEMBLED_AT_RELATIONSHIP_TYPE_NAME = "assembledAt"
_H4_PRODUCT_ENTITY_TYPE_NAME = "Product"
_H4_FACILITY_ENTITY_TYPE_NAME = "Facility"
_H4_CARDINALITY_ID = _uid("h4-assembled-at-cardinality")
_H4_PRODUCT_A_ID = _uid("h4-product-a")
_H4_FACILITY_A_ID = _uid("h4-facility-a")
_H4_ASSEMBLED_AT_EDGE_A_ID = _uid("h4-assembled-at-edge-a")
_H4_PRODUCT_B_ID = _uid("h4-product-b")
_H4_PRODUCT_C_ID = _uid("h4-product-c")
_H4_FACILITY_C2_ID = _uid("h4-facility-c2")
_H4_ASSEMBLED_AT_EDGE_C1_ID = _uid("h4-assembled-at-edge-c1")
_H4_ASSEMBLED_AT_EDGE_C2_ID = _uid("h4-assembled-at-edge-c2")
_H4_SOURCE_SYSTEM_D_ID = _uid("h4-source-system-d")
_H4_SOURCE_OBJECT_D_ID = _uid("h4-source-object-d")
_H4_RESOLUTION_RECORD_D_ID = _uid("h4-resolution-record-d")


class DemoTenantRequiredError(Exception):
    """Raised when the seeder is asked to seed any tenant other than the
    labeled demo tenant."""


@dataclass(frozen=True, slots=True)
class DemoOqiSeedSummary:
    tenant_id: str
    quality_condition_id: str
    supplier_entity_id: UUID
    business_dependency_id: UUID
    reliance_state: str
    accuracy_sap_outcome: str | None
    accuracy_plm_outcome: str | None
    reasonableness_outcome: str | None
    conformity_sap_outcome: str | None
    conformity_plm_outcome: str | None
    h3_consistency_outcome: str | None
    h4_structural_a_outcome: str | None
    h4_structural_b_outcome: str | None
    h4_structural_c_outcome: str | None
    h4_reference_d_outcome: str | None


class DemoOqiSeeder:
    """Manually invoked, idempotent OQI demo-showcase seeder. See this
    module's own docstring for the full input/context/evaluation contract."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def seed(self, *, tenant_id: str = BOOTSTRAP_DEMO_TENANT_ID) -> DemoOqiSeedSummary:
        if tenant_id != BOOTSTRAP_DEMO_TENANT_ID:
            raise DemoTenantRequiredError(
                f"DemoOqiSeeder refuses to seed tenant {tenant_id!r}; "
                f"only {BOOTSTRAP_DEMO_TENANT_ID!r} is permitted"
            )
        dependency_id = self._seed_context(tenant_id)
        return self._evaluate(tenant_id, dependency_id)

    # ------------------------------------------------------------------
    # Input + context only -- never a directly-persisted OQI conclusion.
    # ------------------------------------------------------------------

    def _seed_context(self, tenant_id: str) -> UUID:
        rule_repo = OqiQualityRuleRepositoryImpl(self.session)
        impact_repo = OqiBusinessImpactRepositoryImpl(self.session)
        existing_dependencies = impact_repo.list_active_dependencies_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=_SUPPLIER_ENTITY_ID,
        )
        if rule_repo.get_active(_QUALITY_CONDITION_ID) is not None and existing_dependencies:
            return existing_dependencies[0].dependency_id

        self.session.add(
            SourceSystem(
                source_system_id=_SAP_SYSTEM_ID,
                tenant_id=tenant_id,
                source_system_name="SAP ERP (demo)",
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
            )
        )
        self.session.add(
            SourceSystem(
                source_system_id=_PLM_SYSTEM_ID,
                tenant_id=tenant_id,
                source_system_name="PLM System (demo)",
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
            )
        )
        self.session.flush()

        self.session.add(
            SourceObject(
                source_object_id=_SAP_OBJECT_ID,
                tenant_id=tenant_id,
                source_object_name="SAP Supplier Master (demo)",
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                source_system_id=_SAP_SYSTEM_ID,
            )
        )
        self.session.add(
            SourceObject(
                source_object_id=_PLM_OBJECT_ID,
                tenant_id=tenant_id,
                source_object_name="PLM Supplier Record (demo)",
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                source_system_id=_PLM_SYSTEM_ID,
            )
        )
        self.session.flush()

        field_repo = SourceFieldRepositoryImpl(self.session)
        field_repo.create(
            SourceField(
                source_field_id=Identifier(_SAP_FIELD_ID),
                source_object_id=Identifier(_SAP_OBJECT_ID),
                field_label=CanonicalName("Country of Origin"),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=SEED_TIMESTAMP,
            )
        )
        field_repo.create(
            SourceField(
                source_field_id=Identifier(_PLM_FIELD_ID),
                source_object_id=Identifier(_PLM_OBJECT_ID),
                field_label=CanonicalName("Country of Origin"),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=SEED_TIMESTAMP,
            )
        )
        self.session.flush()

        # Raw evidence -- exactly what a real ingestion pipeline admits.
        # SAP and PLM genuinely disagree; neither is asserted "correct"
        # here or anywhere downstream (majority/authority != truth).
        self.session.add(
            FieldValueEvidenceORM(
                field_value_evidence_id=_uid("sap-evidence"),
                source_field_id=_SAP_FIELD_ID,
                source_record_reference="SUP-DEMO-001",
                observed_representation="US",
                observed_at=SEED_TIMESTAMP,
                received_at=SEED_TIMESTAMP,
            )
        )
        self.session.add(
            FieldValueEvidenceORM(
                field_value_evidence_id=_uid("plm-evidence"),
                source_field_id=_PLM_FIELD_ID,
                source_record_reference="P-DEMO-001",
                observed_representation="MX",
                observed_at=SEED_TIMESTAMP,
                received_at=SEED_TIMESTAMP,
            )
        )
        self.session.flush()

        OqiQualityRuleRepositoryImpl(self.session).create(
            QualityRule.new(
                quality_condition_id=_QUALITY_CONDITION_ID,
                version=1,
                dimension=QualityDimension.CONSISTENCY,
                finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
                validity_primitive=None,
                information_element_requirement_id="ier-country-of-origin",
                rule_parameters={
                    "participants": [
                        {
                            "role": "SAP",
                            "source_field_id": str(_SAP_FIELD_ID),
                            "eligible": True,
                            "expected": True,
                            "authoritative": False,
                        },
                        {
                            "role": "PLM",
                            "source_field_id": str(_PLM_FIELD_ID),
                            "eligible": True,
                            "expected": True,
                            "authoritative": False,
                        },
                    ]
                },
                status=QualityRuleStatus.ACTIVE,
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
            )
        )

        OqiCrossSourceCorrespondenceRepositoryImpl(self.session).create(
            ComparisonSubjectCorrespondence.new(
                comparison_subject_id=_COMPARISON_SUBJECT_ID,
                tenant_id=tenant_id,
                version=1,
                status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
                members=(
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="SAP",
                        source_object_id=_SAP_OBJECT_ID,
                        source_record_reference="SUP-DEMO-001",
                    ),
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="PLM",
                        source_object_id=_PLM_OBJECT_ID,
                        source_record_reference="P-DEMO-001",
                    ),
                ),
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
            )
        )

        # Context: the real-world supplier both source objects describe,
        # and the entity-resolution records binding them to it.
        self.session.add(
            EnterpriseEntity(
                enterprise_entity_id=_SUPPLIER_ENTITY_ID,
                tenant_id=tenant_id,
                enterprise_entity_name="Demo Supplier (OQI Showcase)",
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                entity_type_id=BOOTSTRAP_ENTITY_TYPE_ID,
                business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
            )
        )
        self.session.flush()

        resolution_store = EntityResolutionStore(self.session)
        resolution_store.append(
            EnterpriseEntityResolutionRecord(
                record_id=_uid("resolution-sap"),
                tenant_id=tenant_id,
                enterprise_entity_id=_SUPPLIER_ENTITY_ID,
                supporting_source_object_ids=(_SAP_OBJECT_ID,),
                outcome=ResolutionOutcome.RESOLVED,
                business_confidence=BusinessConfidence.HIGH,
                structured_reasons=("exact match",),
                narrative_explanation="Deterministic OQI demo fixture resolution (SAP).",
                produced_at=SEED_TIMESTAMP,
                policy_version="v1",
            )
        )
        resolution_store.append(
            EnterpriseEntityResolutionRecord(
                record_id=_uid("resolution-plm"),
                tenant_id=tenant_id,
                enterprise_entity_id=_SUPPLIER_ENTITY_ID,
                supporting_source_object_ids=(_PLM_OBJECT_ID,),
                outcome=ResolutionOutcome.RESOLVED,
                business_confidence=BusinessConfidence.HIGH,
                structured_reasons=("exact match",),
                narrative_explanation="Deterministic OQI demo fixture resolution (PLM).",
                produced_at=SEED_TIMESTAMP,
                policy_version="v1",
            )
        )
        self.session.flush()

        # Governed business context -- configuration, never a computed
        # outcome.
        impact_service = OqiBusinessImpactService(self.session)
        process = impact_service.create_process(
            tenant_id=tenant_id,
            name="Supplier Qualification (Demo)",
            description="Deterministic OQI demo-showcase business process.",
            category=BusinessImpactCategory.OPERATIONAL,
            created_by="demo-seeder",
            created_on=SEED_TIMESTAMP,
        )
        dependency = impact_service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=_SUPPLIER_ENTITY_ID,
            criticality=Criticality.HIGH,
            created_by="demo-seeder",
            created_on=SEED_TIMESTAMP,
        )

        self._seed_h2_context(tenant_id)
        self._seed_h3_context(tenant_id)
        self._seed_h4_context(tenant_id)
        return dependency.dependency_id

    def _seed_h2_context(self, tenant_id: str) -> None:
        """CDD-048 §30 (OQI-H2): governed Reference Evidence (shared-
        platform-style governed dataset assertion, PO-02) + one ACCURACY
        QualityRule -- reusing the SAP/PLM Country-of-Origin evidence
        already seeded above, never fabricating new evidence for this
        purpose. Plus one REASONABLENESS BusinessRule on a new raw
        `Order Quantity` observation. No terminal Finding/Impact/Reliance
        row is ever seeded directly -- `_evaluate` invokes the real
        evaluators against exactly this input/context."""
        reference_service = OqiReferenceEvidenceService(
            repository=OqiReferenceEvidenceRepositoryImpl(self.session),
            clock=lambda: SEED_TIMESTAMP,
        )
        # One governed Reference Evidence assertion per source field --
        # each source system's own representation of "Country of Origin"
        # is a distinct anchor (CDD-048 §15), so SAP's and PLM's
        # observations are each independently, honestly compared.
        for field_id in (_SAP_FIELD_ID, _PLM_FIELD_ID):
            reference_service.assert_governed_reference_dataset(
                tenant_id=tenant_id,
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=_SUPPLIER_ENTITY_ID,
                source_field_id=field_id,
                asserted_value="US",
                dataset_name="ISO-3166-1-ALPHA-2 (demo)",
                dataset_version="2024",
                entry_key="US",
                created_by="demo-seeder",
            )

        OqiQualityRuleRepositoryImpl(self.session).create(
            QualityRule.new(
                quality_condition_id=_ACCURACY_QUALITY_CONDITION_ID,
                version=1,
                dimension=QualityDimension.ACCURACY,
                finding_type=QualityFindingType.REFERENCE_VALUE_UNSUPPORTED,
                validity_primitive=None,
                information_element_requirement_id="ier-country-of-origin",
                rule_parameters={},
                status=QualityRuleStatus.ACTIVE,
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
            )
        )

        # Raw evidence for the Reasonableness demo: a negative order
        # quantity on the SAP source object.
        field_repo = SourceFieldRepositoryImpl(self.session)
        field_repo.create(
            SourceField(
                source_field_id=Identifier(_QUANTITY_FIELD_ID),
                source_object_id=Identifier(_SAP_OBJECT_ID),
                field_label=CanonicalName("Order Quantity"),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=SEED_TIMESTAMP,
            )
        )
        self.session.flush()
        self.session.add(
            FieldValueEvidenceORM(
                field_value_evidence_id=_uid("sap-quantity-evidence"),
                source_field_id=_QUANTITY_FIELD_ID,
                source_record_reference="SUP-DEMO-001",
                observed_representation="-5",
                observed_at=SEED_TIMESTAMP,
                received_at=SEED_TIMESTAMP,
            )
        )
        self.session.flush()

        OqiBusinessRuleRepositoryImpl(self.session).create(
            BusinessRule.new(
                business_condition_id=_REASONABLENESS_BUSINESS_CONDITION_ID,
                version=1,
                tenant_id=tenant_id,
                rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
                applicability=ComparatorNode(
                    clause_id="c-applicability",
                    operator=Operator.IS_NOT_NULL,
                    input_role="quantity",
                    comparand_kind=ComparandKind.NONE,
                ),
                predicate=ComparatorNode(
                    clause_id="c-predicate",
                    operator=Operator.GTE,
                    input_role="quantity",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.DECIMAL,
                    literal_value="0",
                ),
                input_bindings=(
                    BusinessRuleInputBinding(
                        input_role="quantity",
                        source_field_id=_QUANTITY_FIELD_ID,
                        required=False,
                        expected_type=ExpectedType.DECIMAL,
                    ),
                ),
                status=BusinessRuleStatus.ACTIVE,
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
                dimension=BusinessRulePurpose.REASONABLENESS,
            )
        )

    def _seed_h3_context(self, tenant_id: str) -> None:
        """CDD-049 §30 (OQI-H3); OQI-H3-I-R1 amendment §5-§6: the genuine
        governed Information Element prerequisite chain, constructed
        entirely through existing, unmodified production code
        (`BlueprintRepositoryImpl.create()`, `SemanticMappingRepositoryImpl.
        create()`) -- never a fake string identifier, never a SourceField
        fallback. A NEW, separately-named, Approved Blueprint ("OQI-H3
        Conformity Demo Blueprint") referencing the already-seeded
        "Supplier" EntityType -- the existing canonical Blueprint (seeded by
        `blueprint_seed.py`) is never touched or superseded. Then the
        governed CanonicalStandard (canonical "USA", alias "US") anchored
        to that real Information Element, plus two Conformity QualityRules
        and one Consistency QualityRule/ComparisonSubjectCorrespondence
        pair, all three sharing the same real
        information_element_requirement_id (PO-H3-01)."""
        supplier_entity_type_id = self.session.scalar(
            select(EntityType.entity_type_id).where(
                EntityType.entity_type_name == _H3_SUPPLIER_ENTITY_TYPE_NAME
            )
        )
        assert supplier_entity_type_id is not None, (
            f"Required governed entity type not found: {_H3_SUPPLIER_ENTITY_TYPE_NAME!r} "
            "-- OntologySeeder must run before DemoOqiSeeder"
        )

        BlueprintRepositoryImpl(self.session).create(
            Blueprint(
                blueprint_id=Identifier(_H3_BLUEPRINT_ID),
                blueprint_name=CanonicalName("OQI-H3 Conformity Demo Blueprint"),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=SEED_TIMESTAMP,
                concept_requirements=(
                    ConceptRequirement(
                        concept_requirement_id=Identifier(_H3_CONCEPT_REQUIREMENT_ID),
                        blueprint_id=Identifier(_H3_BLUEPRINT_ID),
                        entity_type_id=Identifier(supplier_entity_type_id),
                        obligation=Obligation.REQUIRED,
                        information_element_requirements=(
                            InformationElementRequirement(
                                information_element_requirement_id=Identifier(
                                    _H3_INFORMATION_ELEMENT_REQUIREMENT_ID
                                ),
                                concept_requirement_id=Identifier(_H3_CONCEPT_REQUIREMENT_ID),
                                element_name=CanonicalName("Manufacturing Country"),
                                description=Description(
                                    "The governed country in which a supplier's product is "
                                    "manufactured (OQI-H3 demo)."
                                ),
                                obligation=Obligation.REQUIRED,
                            ),
                        ),
                    ),
                ),
            )
        )
        self.session.flush()

        # Two NEW SourceFields on the SAME already-resolved SAP/PLM
        # SourceObjects -- reusing the existing entity resolution (§_seed_
        # context above) so the downstream OQI4/OQI6/Reliance chain applies
        # to these new findings without any new entity-resolution seeding.
        field_repo = SourceFieldRepositoryImpl(self.session)
        field_repo.create(
            SourceField(
                source_field_id=Identifier(_H3_SAP_FIELD_ID),
                source_object_id=Identifier(_SAP_OBJECT_ID),
                field_label=CanonicalName("Manufacturing Country"),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=SEED_TIMESTAMP,
            )
        )
        field_repo.create(
            SourceField(
                source_field_id=Identifier(_H3_PLM_FIELD_ID),
                source_object_id=Identifier(_PLM_OBJECT_ID),
                field_label=CanonicalName("Manufacturing Country"),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=SEED_TIMESTAMP,
            )
        )
        self.session.flush()

        # Raw evidence -- SAP observes the non-canonical alias "US"; PLM
        # observes the governed canonical form "USA" directly. Neither is
        # asserted "correct" here -- Accuracy remains entirely independent
        # of Conformity/Consistency (PO-H3-02).
        self.session.add(
            FieldValueEvidenceORM(
                field_value_evidence_id=_uid("h3-sap-evidence"),
                source_field_id=_H3_SAP_FIELD_ID,
                source_record_reference="SUP-DEMO-001",
                observed_representation="US",
                observed_at=SEED_TIMESTAMP,
                received_at=SEED_TIMESTAMP,
            )
        )
        self.session.add(
            FieldValueEvidenceORM(
                field_value_evidence_id=_uid("h3-plm-evidence"),
                source_field_id=_H3_PLM_FIELD_ID,
                source_record_reference="P-DEMO-001",
                observed_representation="USA",
                observed_at=SEED_TIMESTAMP,
                received_at=SEED_TIMESTAMP,
            )
        )
        self.session.flush()

        # Approved SemanticMapping: proves the genuine SourceField ->
        # SemanticMapping -> InformationElementRequirement resolution path
        # works end-to-end through existing, unmodified governance (CDD-019).
        #
        # Only SAP's mapping is created here, not both. Independently
        # discovered this phase (OQI-H3-I-R1): `SemanticMappingRepositoryImpl.
        # create()` enforces, at the application layer, at most one Approved
        # SemanticMapping per (information_element_requirement_id, tenant) --
        # a pre-existing, CDD-019/H1-era rule, entirely unrelated to and
        # unmodified by H3, which this repository verified is genuinely
        # enforced (`_raise_if_ambiguous`), not merely documented. This means
        # two DIFFERENT SourceFields cannot both hold an Approved mapping to
        # the SAME Information Element simultaneously within one tenant --
        # SemanticMapping is a strict 1:1 correspondence, not many:1.
        #
        # This does not weaken H3's own correctness: neither
        # `OqiConformityEvaluationService` nor the Consistency canonical-
        # projection gate ever queries `semantic_mappings` at evaluation
        # time -- both resolve the applicable Information Element directly
        # from the evaluating `QualityRule.information_element_requirement_id`
        # (CDD-049 §8), which is set identically, correctly, for BOTH the
        # SAP and PLM Conformity rules below regardless of SemanticMapping
        # state. PLM's own convergence on the same governed Information
        # Element is therefore proven by its QualityRule's own field, not by
        # a second (architecturally disallowed) Approved SemanticMapping row.
        SemanticMappingRepositoryImpl(self.session).create(
            SemanticMapping(
                semantic_mapping_id=Identifier(_H3_SAP_SEMANTIC_MAPPING_ID),
                source_field_id=Identifier(_H3_SAP_FIELD_ID),
                information_element_requirement_id=Identifier(
                    _H3_INFORMATION_ELEMENT_REQUIREMENT_ID
                ),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=SEED_TIMESTAMP,
            )
        )
        self.session.flush()

        # Governed CanonicalStandard: canonical "USA", recognized alias
        # "US" -- shared-platform, anchored exclusively to the real
        # Information Element (CDD-049 §9-§11).
        OqiCanonicalStandardRepositoryImpl(self.session).insert_standard(
            CanonicalStandard(
                canonical_standard_id=_H3_CANONICAL_STANDARD_ID,
                information_element_requirement_id=_H3_INFORMATION_ELEMENT_REQUIREMENT_ID,
                version_number=1,
                previous_version_id=None,
                status=CanonicalStandardStatus.ACTIVE,
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
                values=(
                    CanonicalValue(
                        canonical_value_id=_H3_CANONICAL_VALUE_ID,
                        canonical_standard_id=_H3_CANONICAL_STANDARD_ID,
                        canonical_representation="USA",
                        aliases=(
                            CanonicalAlias(
                                canonical_alias_id=_H3_CANONICAL_ALIAS_ID,
                                canonical_value_id=_H3_CANONICAL_VALUE_ID,
                                alias_representation="US",
                            ),
                        ),
                    ),
                ),
            )
        )
        self.session.flush()

        # Two Conformity QualityRules (one per source field) -- both
        # sharing the real information_element_requirement_id, resolved
        # dynamically per observation (CDD-049 §6, never configured
        # per-rule).
        quality_rule_repo = OqiQualityRuleRepositoryImpl(self.session)
        quality_rule_repo.create(
            QualityRule.new(
                quality_condition_id=_H3_SAP_CONFORMITY_CONDITION_ID,
                version=1,
                dimension=QualityDimension.CONFORMITY,
                finding_type=QualityFindingType.NON_CANONICAL_REPRESENTATION,
                validity_primitive=None,
                information_element_requirement_id=str(_H3_INFORMATION_ELEMENT_REQUIREMENT_ID),
                rule_parameters={},
                status=QualityRuleStatus.ACTIVE,
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
            )
        )
        quality_rule_repo.create(
            QualityRule.new(
                quality_condition_id=_H3_PLM_CONFORMITY_CONDITION_ID,
                version=1,
                dimension=QualityDimension.CONFORMITY,
                finding_type=QualityFindingType.NON_CANONICAL_REPRESENTATION,
                validity_primitive=None,
                information_element_requirement_id=str(_H3_INFORMATION_ELEMENT_REQUIREMENT_ID),
                rule_parameters={},
                status=QualityRuleStatus.ACTIVE,
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
            )
        )

        # One Consistency QualityRule + ComparisonSubjectCorrespondence for
        # the SAME two fields, ALSO carrying the real
        # information_element_requirement_id -- this is what the G0
        # canonical-projection gate (CDD-049 §16) resolves against.
        quality_rule_repo.create(
            QualityRule.new(
                quality_condition_id=_H3_CONSISTENCY_CONDITION_ID,
                version=1,
                dimension=QualityDimension.CONSISTENCY,
                finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
                validity_primitive=None,
                information_element_requirement_id=str(_H3_INFORMATION_ELEMENT_REQUIREMENT_ID),
                rule_parameters={
                    "participants": [
                        {
                            "role": "SAP",
                            "source_field_id": str(_H3_SAP_FIELD_ID),
                            "eligible": True,
                            "expected": True,
                            "authoritative": False,
                        },
                        {
                            "role": "PLM",
                            "source_field_id": str(_H3_PLM_FIELD_ID),
                            "eligible": True,
                            "expected": True,
                            "authoritative": False,
                        },
                    ]
                },
                status=QualityRuleStatus.ACTIVE,
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
            )
        )

        OqiCrossSourceCorrespondenceRepositoryImpl(self.session).create(
            ComparisonSubjectCorrespondence.new(
                comparison_subject_id=_H3_COMPARISON_SUBJECT_ID,
                tenant_id=tenant_id,
                version=1,
                status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
                members=(
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="SAP",
                        source_object_id=_SAP_OBJECT_ID,
                        source_record_reference="SUP-DEMO-001",
                    ),
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="PLM",
                        source_object_id=_PLM_OBJECT_ID,
                        source_record_reference="P-DEMO-001",
                    ),
                ),
                created_by="demo-seeder",
                created_on=SEED_TIMESTAMP,
            )
        )

    def _seed_h4_context(self, tenant_id: str) -> None:
        """CDD-050 §28: the ALREADY-GOVERNED, real `assembledAt`
        RelationshipRequirement (Product -> Facility, REQUIRED) -- zero new
        Blueprint/ConceptRequirement/RelationshipRequirement (PO governed
        seed material, unmodified). One new ACTIVE
        `IntegrityRelationshipCardinality` (min=1, max=1) anchors it; real
        `EnterpriseEntity`/`InstitutionalRelationship` rows for scenarios
        A/B/C; one real `ResolutionOutcome.UNRESOLVED` record for scenario
        D. No Integrity evaluation/Finding row is directly inserted here --
        those arise only through `_evaluate_h4`'s calls to the real
        Structural/Reference evaluation services (CDD-050 §34)."""
        relationship_type_id = self.session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == _H4_ASSEMBLED_AT_RELATIONSHIP_TYPE_NAME
            )
        )
        assert relationship_type_id is not None, (
            f"Required governed relationship type not found: "
            f"{_H4_ASSEMBLED_AT_RELATIONSHIP_TYPE_NAME!r} -- OntologySeeder must run before "
            "DemoOqiSeeder"
        )
        relationship_requirement_id = self.session.scalar(
            select(RelationshipRequirementORM.relationship_requirement_id).where(
                RelationshipRequirementORM.relationship_type_id == relationship_type_id
            )
        )
        assert relationship_requirement_id is not None, (
            "Required governed RelationshipRequirement not found for "
            f"{_H4_ASSEMBLED_AT_RELATIONSHIP_TYPE_NAME!r} -- BlueprintSeeder must run before "
            "DemoOqiSeeder"
        )
        product_type_id = self.session.scalar(
            select(EntityType.entity_type_id).where(
                EntityType.entity_type_name == _H4_PRODUCT_ENTITY_TYPE_NAME
            )
        )
        facility_type_id = self.session.scalar(
            select(EntityType.entity_type_id).where(
                EntityType.entity_type_name == _H4_FACILITY_ENTITY_TYPE_NAME
            )
        )
        assert product_type_id is not None and facility_type_id is not None, (
            f"Required governed entity types not found: {_H4_PRODUCT_ENTITY_TYPE_NAME!r} / "
            f"{_H4_FACILITY_ENTITY_TYPE_NAME!r} -- OntologySeeder must run before DemoOqiSeeder"
        )

        requirement_repo = OqiIntegrityRequirementRepositoryImpl(self.session)
        if (
            requirement_repo.get_active_cardinality_for_requirement(
                relationship_requirement_id=relationship_requirement_id
            )
            is None
        ):
            requirement_repo.insert_cardinality(
                IntegrityRelationshipCardinality(
                    integrity_relationship_cardinality_id=_H4_CARDINALITY_ID,
                    relationship_requirement_id=relationship_requirement_id,
                    min_cardinality=1,
                    max_cardinality=1,
                    version_number=1,
                    previous_version_id=None,
                    status=IntegrityRelationshipCardinalityStatus.ACTIVE,
                    created_by="demo-seeder",
                    created_on=SEED_TIMESTAMP,
                )
            )

        def _entity(entity_id: UUID, name: str, type_id: UUID) -> None:
            existing = self.session.get(EnterpriseEntity, entity_id)
            if existing is not None:
                return
            self.session.add(
                EnterpriseEntity(
                    enterprise_entity_id=entity_id,
                    tenant_id=tenant_id,
                    enterprise_entity_name=name,
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                    entity_type_id=type_id,
                    business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
                )
            )

        def _edge(edge_id: UUID, name: str, from_id: UUID, to_id: UUID) -> None:
            existing = self.session.get(InstitutionalRelationship, edge_id)
            if existing is not None:
                return
            self.session.add(
                InstitutionalRelationship(
                    institutional_relationship_id=edge_id,
                    tenant_id=tenant_id,
                    institutional_relationship_name=name,
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                    relationship_type_id=relationship_type_id,
                    from_entity_id=from_id,
                    to_entity_id=to_id,
                )
            )

        # Scenario A: one qualifying edge -> SATISFIED.
        _entity(_H4_PRODUCT_A_ID, "H4 Demo Product A", product_type_id)
        _entity(_H4_FACILITY_A_ID, "H4 Demo Facility A", facility_type_id)
        self.session.flush()
        _edge(
            _H4_ASSEMBLED_AT_EDGE_A_ID, "H4 Demo A assembledAt", _H4_PRODUCT_A_ID, _H4_FACILITY_A_ID
        )

        # Scenario B: zero qualifying edges -> MISSING_REQUIRED_RELATIONSHIP.
        _entity(_H4_PRODUCT_B_ID, "H4 Demo Product B", product_type_id)

        # Scenario C: two distinct qualifying targets -> RELATIONSHIP_
        # CARDINALITY_VIOLATION (reuses Facility A as one of the two
        # distinct targets, per PO-H4-01's distinct-target-counting rule).
        _entity(_H4_PRODUCT_C_ID, "H4 Demo Product C", product_type_id)
        _entity(_H4_FACILITY_C2_ID, "H4 Demo Facility C2", facility_type_id)
        self.session.flush()
        _edge(
            _H4_ASSEMBLED_AT_EDGE_C1_ID,
            "H4 Demo C assembledAt 1",
            _H4_PRODUCT_C_ID,
            _H4_FACILITY_A_ID,
        )
        _edge(
            _H4_ASSEMBLED_AT_EDGE_C2_ID,
            "H4 Demo C assembledAt 2",
            _H4_PRODUCT_C_ID,
            _H4_FACILITY_C2_ID,
        )
        self.session.flush()

        # Scenario D: a genuinely evaluated, persisted ResolutionOutcome
        # .UNRESOLVED -- Reference Integrity's own orphan proof (CDD-050
        # §20: only a real persisted UNRESOLVED record establishes an
        # orphan, never a fabricated target).
        existing_system = self.session.get(SourceSystem, _H4_SOURCE_SYSTEM_D_ID)
        if existing_system is None:
            self.session.add(
                SourceSystem(
                    source_system_id=_H4_SOURCE_SYSTEM_D_ID,
                    tenant_id=tenant_id,
                    source_system_name="H4 Demo Source System D",
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                )
            )
            self.session.flush()
        existing_object = self.session.get(SourceObject, _H4_SOURCE_OBJECT_D_ID)
        if existing_object is None:
            self.session.add(
                SourceObject(
                    source_object_id=_H4_SOURCE_OBJECT_D_ID,
                    tenant_id=tenant_id,
                    source_object_name="H4 Demo Source Object D",
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                    source_system_id=_H4_SOURCE_SYSTEM_D_ID,
                )
            )
            self.session.flush()

        resolution_store = EntityResolutionStore(self.session)
        if (
            resolution_store.get_current_record(
                tenant_id,
                EntityResolutionStore.understanding_key((_H4_SOURCE_OBJECT_D_ID,)),
            )
            is None
        ):
            resolution_store.append(
                EnterpriseEntityResolutionRecord(
                    record_id=_H4_RESOLUTION_RECORD_D_ID,
                    tenant_id=tenant_id,
                    enterprise_entity_id=None,
                    supporting_source_object_ids=(_H4_SOURCE_OBJECT_D_ID,),
                    outcome=ResolutionOutcome.UNRESOLVED,
                    business_confidence=BusinessConfidence.HIGH,
                    structured_reasons=("no matching enterprise entity",),
                    narrative_explanation=(
                        "Deterministic OQI-H4 demo fixture: genuinely evaluated, unresolved."
                    ),
                    produced_at=SEED_TIMESTAMP,
                    policy_version="v1",
                )
            )
        self.session.flush()

    # ------------------------------------------------------------------
    # Real, unmodified production evaluators -- never a directly-persisted
    # conclusion. Re-run every invocation; each is independently
    # idempotent by its own existing digest/ledger design.
    # ------------------------------------------------------------------

    def _evaluate(self, tenant_id: str, dependency_id: UUID) -> DemoOqiSeedSummary:
        # A fixed clock -- never datetime.now() -- keeps every re-seed's
        # derived evaluation_horizon (and therefore evaluation_id) identical,
        # which is what makes re-running seed() a genuine no-op.
        def clock() -> datetime:
            return SEED_TIMESTAMP

        rule = OqiQualityRuleRepositoryImpl(self.session).get_active(_QUALITY_CONDITION_ID)
        assert rule is not None
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(self.session).get_active(
            tenant_id=tenant_id, comparison_subject_id=_COMPARISON_SUBJECT_ID
        )
        assert correspondence is not None
        OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(self.session), clock=clock
        ).evaluate_current_state(rule=rule, correspondence=correspondence)
        self.session.flush()

        finding_id = derive_comparison_finding_id(
            tenant_id=tenant_id,
            quality_condition_id=_QUALITY_CONDITION_ID,
            comparison_subject_id=_COMPARISON_SUBJECT_ID,
        )
        OqiOntologyImpactEvaluationService(
            OqiOntologyImpactEvaluationRepositoryImpl(self.session), clock=clock
        ).evaluate_current_state(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        self.session.flush()

        impact_service = OqiBusinessImpactService(self.session)
        impact_service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dependency_id, evaluated_at=SEED_TIMESTAMP
        )
        reliance = impact_service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=_SUPPLIER_ENTITY_ID,
            evaluated_at=SEED_TIMESTAMP,
        )
        self.session.flush()

        accuracy_sap, accuracy_plm, reasonableness = self._evaluate_h2(tenant_id, clock)
        conformity_sap, conformity_plm, h3_consistency = self._evaluate_h3(tenant_id, clock)
        structural_a, structural_b, structural_c, reference_d = self._evaluate_h4(tenant_id, clock)

        return DemoOqiSeedSummary(
            tenant_id=tenant_id,
            quality_condition_id=_QUALITY_CONDITION_ID,
            supplier_entity_id=_SUPPLIER_ENTITY_ID,
            business_dependency_id=dependency_id,
            reliance_state=reliance.state.value,
            accuracy_sap_outcome=accuracy_sap,
            accuracy_plm_outcome=accuracy_plm,
            reasonableness_outcome=reasonableness,
            conformity_sap_outcome=conformity_sap,
            conformity_plm_outcome=conformity_plm,
            h3_consistency_outcome=h3_consistency,
            h4_structural_a_outcome=structural_a,
            h4_structural_b_outcome=structural_b,
            h4_structural_c_outcome=structural_c,
            h4_reference_d_outcome=reference_d,
        )

    def _evaluate_h2(
        self, tenant_id: str, clock: Callable[[], datetime]
    ) -> tuple[str | None, str | None, str | None]:
        """CDD-048 §30: calls the real, unmodified-by-reuse OQI-H2
        evaluators -- `OqiAccuracyEvaluationService.evaluate_current_state`
        (twice, once per source field/observation) and
        `OqiBusinessRuleEvaluationService.evaluate_current_state` (the
        dimension=REASONABLENESS rule) -- so every Accuracy/Reasonableness
        outcome a fresh demo shows is real evaluator output over real seeded
        evidence and governed Reference Evidence, never a directly-persisted
        conclusion."""
        accuracy_service = OqiAccuracyEvaluationService(
            evaluation_repository=OqiAccuracyEvaluationRepositoryImpl(self.session),
            reference_evidence_lookup=OqiReferenceEvidenceService(
                repository=OqiReferenceEvidenceRepositoryImpl(self.session), clock=clock
            ),
            clock=clock,
        )
        accuracy_rule = OqiQualityRuleRepositoryImpl(self.session).get_active(
            _ACCURACY_QUALITY_CONDITION_ID
        )
        assert accuracy_rule is not None

        sap_evaluation = accuracy_service.evaluate_current_state(
            rule=accuracy_rule,
            subject=EvaluationSubject(
                lineage=SourceRecordLineageIdentity(
                    tenant_id=tenant_id,
                    source_object_id=_SAP_OBJECT_ID,
                    source_record_reference="SUP-DEMO-001",
                ),
                source_field_id=_SAP_FIELD_ID,
            ),
        )
        self.session.flush()
        plm_evaluation = accuracy_service.evaluate_current_state(
            rule=accuracy_rule,
            subject=EvaluationSubject(
                lineage=SourceRecordLineageIdentity(
                    tenant_id=tenant_id,
                    source_object_id=_PLM_OBJECT_ID,
                    source_record_reference="P-DEMO-001",
                ),
                source_field_id=_PLM_FIELD_ID,
            ),
        )
        self.session.flush()

        reasonableness_rule = OqiBusinessRuleRepositoryImpl(self.session).get_active(
            tenant_id=tenant_id, business_condition_id=_REASONABLENESS_BUSINESS_CONDITION_ID
        )
        assert reasonableness_rule is not None
        reasonableness_service = OqiBusinessRuleEvaluationService(
            evaluation_repository=OqiBusinessRuleEvaluationRepositoryImpl(self.session),
            evidence_value_reader=OqiBusinessRuleEvidenceValueReader(self.session),
            clock=clock,
        )
        reasonableness_evaluation = reasonableness_service.evaluate_current_state(
            rule=reasonableness_rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=_SAP_OBJECT_ID,
                source_record_reference="SUP-DEMO-001",
            ),
        )
        self.session.flush()

        return (
            None if sap_evaluation is None else sap_evaluation.outcome.value,
            None if plm_evaluation is None else plm_evaluation.outcome.value,
            None if reasonableness_evaluation is None else reasonableness_evaluation.outcome.value,
        )

    def _evaluate_h3(
        self, tenant_id: str, clock: Callable[[], datetime]
    ) -> tuple[str | None, str | None, str | None]:
        """CDD-049 §30: calls the real, unmodified-by-reuse OQI-H3
        evaluators -- `OqiConformityEvaluationService.evaluate_current_state`
        (twice, once per source field/observation) and
        `OqiCrossSourceEvaluationService.evaluate_current_state` (the new
        Consistency rule, this time constructed WITH a real
        `canonical_standard_lookup`) -- so every Conformity/Consistency
        outcome a fresh demo shows is real evaluator output over real seeded
        evidence and a real governed CanonicalStandard, never a
        directly-persisted conclusion."""
        canonical_standard_repo = OqiCanonicalStandardRepositoryImpl(self.session)
        conformity_service = OqiConformityEvaluationService(
            evaluation_repository=OqiConformityEvaluationRepositoryImpl(self.session),
            canonical_standard_lookup=canonical_standard_repo,
            clock=clock,
        )
        sap_conformity_rule = OqiQualityRuleRepositoryImpl(self.session).get_active(
            _H3_SAP_CONFORMITY_CONDITION_ID
        )
        assert sap_conformity_rule is not None
        sap_conformity = conformity_service.evaluate_current_state(
            rule=sap_conformity_rule,
            subject=EvaluationSubject(
                lineage=SourceRecordLineageIdentity(
                    tenant_id=tenant_id,
                    source_object_id=_SAP_OBJECT_ID,
                    source_record_reference="SUP-DEMO-001",
                ),
                source_field_id=_H3_SAP_FIELD_ID,
            ),
        )
        self.session.flush()

        plm_conformity_rule = OqiQualityRuleRepositoryImpl(self.session).get_active(
            _H3_PLM_CONFORMITY_CONDITION_ID
        )
        assert plm_conformity_rule is not None
        plm_conformity = conformity_service.evaluate_current_state(
            rule=plm_conformity_rule,
            subject=EvaluationSubject(
                lineage=SourceRecordLineageIdentity(
                    tenant_id=tenant_id,
                    source_object_id=_PLM_OBJECT_ID,
                    source_record_reference="P-DEMO-001",
                ),
                source_field_id=_H3_PLM_FIELD_ID,
            ),
        )
        self.session.flush()

        h3_consistency_rule = OqiQualityRuleRepositoryImpl(self.session).get_active(
            _H3_CONSISTENCY_CONDITION_ID
        )
        assert h3_consistency_rule is not None
        h3_correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(self.session).get_active(
            tenant_id=tenant_id, comparison_subject_id=_H3_COMPARISON_SUBJECT_ID
        )
        assert h3_correspondence is not None
        h3_consistency_evaluation = OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(self.session),
            canonical_standard_lookup=canonical_standard_repo,
            clock=clock,
        ).evaluate_current_state(rule=h3_consistency_rule, correspondence=h3_correspondence)
        self.session.flush()

        return (
            None if sap_conformity is None else sap_conformity.outcome.value,
            None if plm_conformity is None else plm_conformity.outcome.value,
            None if h3_consistency_evaluation is None else h3_consistency_evaluation.outcome.value,
        )

    def _evaluate_h4(
        self, tenant_id: str, clock: Callable[[], datetime]
    ) -> tuple[str | None, str | None, str | None, str | None]:
        """CDD-050 §28, §34: calls the real, unmodified-by-reuse OQI-H4
        evaluators -- `OqiIntegrityStructuralEvaluationService.
        evaluate_current_state` (scenarios A/B/C) and
        `OqiIntegrityReferenceEvaluationService.evaluate_current_state`
        (scenario D) -- so every Structural/Reference Integrity outcome a
        fresh demo shows is real evaluator output over real seeded
        entities/relationships/resolution state, never a directly-persisted
        conclusion."""
        relationship_type_id = self.session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == _H4_ASSEMBLED_AT_RELATIONSHIP_TYPE_NAME
            )
        )
        assert relationship_type_id is not None
        relationship_requirement_id = self.session.scalar(
            select(RelationshipRequirementORM.relationship_requirement_id).where(
                RelationshipRequirementORM.relationship_type_id == relationship_type_id
            )
        )
        assert relationship_requirement_id is not None

        requirement_repo = OqiIntegrityRequirementRepositoryImpl(self.session)
        structural_service = OqiIntegrityStructuralEvaluationService(
            evaluation_repository=OqiIntegrityStructuralEvaluationRepositoryImpl(self.session),
            cardinality_lookup=requirement_repo,
            clock=clock,
        )
        eval_a = structural_service.evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=_H4_PRODUCT_A_ID,
            relationship_requirement_id=relationship_requirement_id,
        )
        self.session.flush()
        eval_b = structural_service.evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=_H4_PRODUCT_B_ID,
            relationship_requirement_id=relationship_requirement_id,
        )
        self.session.flush()
        eval_c = structural_service.evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=_H4_PRODUCT_C_ID,
            relationship_requirement_id=relationship_requirement_id,
        )
        self.session.flush()

        reference_service = OqiIntegrityReferenceEvaluationService(
            evaluation_repository=OqiIntegrityReferenceEvaluationRepositoryImpl(self.session),
            clock=clock,
        )
        eval_d = reference_service.evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=_H4_SOURCE_OBJECT_D_ID,
            relationship_requirement_id=relationship_requirement_id,
        )
        self.session.flush()

        return (
            None if eval_a is None else eval_a.outcome.value,
            None if eval_b is None else eval_b.outcome.value,
            None if eval_c is None else eval_c.outcome.value,
            None if eval_d is None else eval_d.outcome.value,
        )


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings

    settings = get_settings()
    assert settings.database_url is not None, "CTEC_DATABASE_URL must be set to run this seeder"
    engine = create_engine(settings.database_url)
    factory = sessionmaker(engine)
    with factory() as session:
        summary = DemoOqiSeeder(session).seed()
        session.commit()
    print(f"[demo_oqi_seeder] {summary}")
