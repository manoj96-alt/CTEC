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

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.application.oqi_ontology_impact_evaluation_service import (
    OqiOntologyImpactEvaluationService,
)
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EnterpriseEntityResolutionRecord,
    ResolutionOutcome,
)
from app.domain.integration import SourceField
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_business_impact.dependency import Criticality
from app.domain.oqi_business_impact.process import BusinessImpactCategory
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
from app.domain.oqi_ontology_impact.evaluation import FindingFamily, OntologyElementType
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
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
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
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
        return dependency.dependency_id

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

        return DemoOqiSeedSummary(
            tenant_id=tenant_id,
            quality_condition_id=_QUALITY_CONDITION_ID,
            supplier_entity_id=_SUPPLIER_ENTITY_ID,
            business_dependency_id=dependency_id,
            reliance_state=reliance.state.value,
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
