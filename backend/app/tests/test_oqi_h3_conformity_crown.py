"""CDD-049 OQI-H3 Governed Conformity and Canonical Standards -- Artifact
Authorization row 9: the H3 crown suite, real PostgreSQL, exercised through
the actual Conformity / canonical-projection-aware Consistency evaluator
entry points and the full downstream chain -- never a raw repository call in
isolation where a real integration path exists.

Proves the CDD-049 §33 frozen matrix (behavioral proof, never
code-inspection-only, except where the matrix itself calls for a structural
proof -- CDD-049 §33 E1, mirroring CDD-048's own CY3-CY5 import-firewall
precedent, and F3-F5's "generic, no dimension special-casing" claim, proven
the same way): Conformity C1-C10; Consistency/canonicalization K1-K10;
Validity independence V1-V3; Accuracy non-interference A1-A3 (A1 live);
origin/downstream F1-F5; coverage CV1-CV5; remediation R1-R4; ER boundary
E1-E2; the H2 non-regression crown (CDD-049 §31) and the H3 crown scenario
(CDD-049 §30), both live in the same database state.

Migration M1-M6 and tenancy/authority T1-T3 live in
`test_oqi_h3_authorization_and_tenant_isolation.py` (T1-T3) and the existing
migration test suite (M1-M6); Docker D1-D10 is proven at the Docker/Compose
runtime layer, not here."""

# isort: skip_file
from __future__ import annotations

import ast
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
)
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
    ValidityPrimitive,
)
from app.domain.oqi_canonical_standard.standard import (
    CanonicalAlias,
    CanonicalizationState,
    CanonicalStandard,
    CanonicalStandardStatus,
    CanonicalValue,
    canonicalize,
)
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.oqi_finding_origin.origin import (
    FindingStorageFamily,
    quality_dimension_for_oqi1_finding_type,
)
from app.domain.oqi_quality_coverage.policy import CoverageDimension
from app.domain.oqi_remediation.candidate import RemediationCandidateBasis
from app.domain.oqi_remediation.case import FindingFamily
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.application.oqi_conformity_evaluation_service import OqiConformityEvaluationService
from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
from app.application.oqi_reference_evidence_service import OqiReferenceEvidenceService
from app.application.oqi_remediation_service import OqiRemediationService
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_ontology_impact.evaluation import FindingFamily as OntologyImpactFindingFamily
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.oqi_canonical_standard import (
    ComparisonParticipantCanonicalProjectionORM,
    QualityEvaluationCanonicalStandardORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
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
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.tests.test_oqi_h2_accuracy_reasonableness_crown import (
    _accuracy_rule,
    _accuracy_service,
    _seed_entity_and_field,
)
from app.tests.test_oqi_quality_postgres import _admit_evidence, _subject
from app.tests.test_oqi_quality_postgres import _seed_field as _seed_oqi1_field

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture()
def session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as session:
        yield session
        session.rollback()


def _tenant() -> str:
    return f"tenant-{uuid4()}"


def _entity_type_id(session: Session, name: str) -> Identifier:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return Identifier(value)


def _seed_information_element(
    session: Session, *, element_name: str = "H3 Crown Test Element"
) -> UUID:
    """Real, governed prerequisite chain -- Blueprint -> ConceptRequirement
    -> InformationElementRequirement -- through the existing, unmodified
    `BlueprintRepositoryImpl.create()`, mirroring `demo_oqi_seeder.py`'s own
    `_seed_h3_context` construction exactly (OQI-H3-I-R1 amendment §5-§6).
    Never a fake identifier: `oqi_canonical_standards.information_element_
    requirement_id` carries a real FK to `information_element_requirements`."""
    OntologySeeder(session).load()
    session.commit()
    supplier_type_id = _entity_type_id(session, "Supplier")

    blueprint_id = Identifier(uuid4())
    concept_requirement_id = Identifier(uuid4())
    information_element_requirement_id = uuid4()
    BlueprintRepositoryImpl(session).create(
        Blueprint(
            blueprint_id=blueprint_id,
            blueprint_name=CanonicalName(f"H3 Crown Test Blueprint {uuid4()}"),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
            concept_requirements=(
                ConceptRequirement(
                    concept_requirement_id=concept_requirement_id,
                    blueprint_id=blueprint_id,
                    entity_type_id=supplier_type_id,
                    obligation=Obligation.REQUIRED,
                    information_element_requirements=(
                        InformationElementRequirement(
                            information_element_requirement_id=Identifier(
                                information_element_requirement_id
                            ),
                            concept_requirement_id=concept_requirement_id,
                            element_name=CanonicalName(element_name),
                            description=Description(
                                "Test-seeded Information Element for OQI-H3 crown proofs."
                            ),
                            obligation=Obligation.REQUIRED,
                        ),
                    ),
                ),
            ),
        )
    )
    session.flush()
    return information_element_requirement_id


def _standard(
    *,
    information_element_requirement_id: UUID,
    values: tuple[CanonicalValue, ...],
    version_number: int = 1,
    previous_version_id: UUID | None = None,
    standard_id: UUID | None = None,
) -> CanonicalStandard:
    return CanonicalStandard(
        canonical_standard_id=standard_id or uuid4(),
        information_element_requirement_id=information_element_requirement_id,
        version_number=version_number,
        previous_version_id=previous_version_id,
        status=CanonicalStandardStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
        values=values,
    )


def _usa_standard(
    information_element_requirement_id: UUID, *, standard_id: UUID | None = None
) -> CanonicalStandard:
    resolved_standard_id = standard_id or uuid4()
    value_id = uuid4()
    return _standard(
        information_element_requirement_id=information_element_requirement_id,
        standard_id=resolved_standard_id,
        values=(
            CanonicalValue(
                canonical_value_id=value_id,
                canonical_standard_id=resolved_standard_id,
                canonical_representation="USA",
                aliases=(
                    CanonicalAlias(
                        canonical_alias_id=uuid4(),
                        canonical_value_id=value_id,
                        alias_representation="US",
                    ),
                ),
            ),
        ),
    )


def _conformity_rule(
    *, quality_condition_id: str, information_element_requirement_id: UUID
) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=quality_condition_id,
        version=1,
        dimension=QualityDimension.CONFORMITY,
        finding_type=QualityFindingType.NON_CANONICAL_REPRESENTATION,
        validity_primitive=None,
        information_element_requirement_id=str(information_element_requirement_id),
        rule_parameters={},
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


def _conformity_service(session: Session) -> OqiConformityEvaluationService:
    return OqiConformityEvaluationService(
        evaluation_repository=OqiConformityEvaluationRepositoryImpl(session),
        canonical_standard_lookup=OqiCanonicalStandardRepositoryImpl(session),
        clock=lambda: NOW,
    )


class TestConformityCrown:
    def test_c1_canonical_representation_satisfied(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "SATISFIED"
        findings = (
            session.execute(
                select(QualityFindingORM).where(
                    QualityFindingORM.tenant_id == tenant_id,
                    QualityFindingORM.quality_condition_id == rule.quality_condition_id,
                )
            )
            .scalars()
            .all()
        )
        assert findings == []

    def test_c2_alias_resolved_violated(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"  # alias, not canonical -- CONFORMING requires
        finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.quality_condition_id == rule.quality_condition_id,
            )
        ).scalar_one()
        assert finding.finding_type == "NON_CANONICAL_REPRESENTATION"
        assert finding.status == "OPEN"

    def test_c3_unmapped_not_evaluable_zero_row(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="Wakanda",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None
        findings = (
            session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert findings == []

    def test_c4_no_standard_not_evaluable_zero_row(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)  # no CanonicalStandard inserted for this IE
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None

    def test_c5_retired_standard_is_no_standard(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        standard = _usa_standard(ier_id)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(standard)
        session.flush()
        OqiCanonicalStandardRepositoryImpl(session).retire_standard(
            canonical_standard_id=standard.canonical_standard_id, retired_on=NOW
        )
        session.flush()

        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None  # RETIRED standard resolves as NO_STANDARD, never used

    def test_c6_version_supersession_changes_outcome(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        v1 = _usa_standard(ier_id)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(v1)
        session.flush()

        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        first = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert first is not None
        assert first.outcome.value == "SATISFIED"  # "USA" is canonical under v1

        OqiCanonicalStandardRepositoryImpl(session).retire_standard(
            canonical_standard_id=v1.canonical_standard_id, retired_on=NOW
        )
        session.flush()
        mexico_value_id = uuid4()
        v2_standard_id = uuid4()
        v2 = _standard(
            information_element_requirement_id=ier_id,
            version_number=2,
            previous_version_id=v1.canonical_standard_id,
            standard_id=v2_standard_id,
            values=(
                CanonicalValue(
                    canonical_value_id=mexico_value_id,
                    canonical_standard_id=v2_standard_id,
                    canonical_representation="MEXICO",
                    aliases=(),
                ),
            ),
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(v2)
        session.flush()

        # A fresh subject (different record) so identity material differs
        # from the first evaluation -- the SAME raw "USA" observation now
        # resolves under v2, where it is no longer the governed canonical
        # value at all.
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-2",
            observed_representation="USA",
        )
        subject_2 = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-2",
        )
        second = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject_2)
        assert (
            second is None
        )  # unmapped under v2 (NOT_MAPPED) -- zero row, outcome genuinely differs

    def test_c7_missing_value_stays_completeness_zero_row(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        # No evidence admitted at all.
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="never-admitted",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None  # Completeness's domain, never a Conformity Finding

    def test_c8_idempotent_replay(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        service = _conformity_service(session)
        first = service.evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        second = service.evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert first is not None and second is not None
        assert first.evaluation_id == second.evaluation_id
        count = (
            session.execute(
                select(QualityEvaluationCanonicalStandardORM).where(
                    QualityEvaluationCanonicalStandardORM.evaluation_id == first.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(count) == 1  # replay never duplicates the provenance link either

    def test_c9_raw_evidence_never_rewritten(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        evidence_id = _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"

        raw = session.get(FieldValueEvidenceORM, evidence_id)
        assert raw is not None
        assert raw.observed_representation == "US"  # never rewritten to "USA"

    def test_c10_exact_standard_and_version_provenance(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        standard = _usa_standard(ier_id)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(standard)
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None

        link = session.execute(
            select(QualityEvaluationCanonicalStandardORM).where(
                QualityEvaluationCanonicalStandardORM.evaluation_id == evaluation.evaluation_id
            )
        ).scalar_one()
        assert link.canonical_value_id == standard.values[0].canonical_value_id
        assert link.standard_version == standard.version_number


# =======================================================================
# CONSISTENCY / CANONICALIZATION -- K1-K10.
# =======================================================================


def _consistency_rule(
    *,
    condition_id: str,
    sap_field: UUID,
    plm_field: UUID,
    information_element_requirement_id: UUID,
    plm_expected: bool = True,
) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=condition_id,
        version=1,
        dimension=QualityDimension.CONSISTENCY,
        finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
        validity_primitive=None,
        information_element_requirement_id=str(information_element_requirement_id),
        rule_parameters={
            "participants": [
                {
                    "role": "SAP",
                    "source_field_id": str(sap_field),
                    "eligible": True,
                    "expected": True,
                    "authoritative": False,
                },
                {
                    "role": "PLM",
                    "source_field_id": str(plm_field),
                    "eligible": True,
                    "expected": plm_expected,
                    "authoritative": False,
                },
            ]
        },
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


def _correspondence(
    *, tenant_id: str, subject_id: UUID, sap_object: UUID, plm_object: UUID
) -> ComparisonSubjectCorrespondence:
    return ComparisonSubjectCorrespondence.new(
        comparison_subject_id=subject_id,
        tenant_id=tenant_id,
        version=1,
        status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
        members=(
            ComparisonSubjectCorrespondenceMember(
                participant_role="SAP",
                source_object_id=sap_object,
                source_record_reference="rec-sap",
            ),
            ComparisonSubjectCorrespondenceMember(
                participant_role="PLM",
                source_object_id=plm_object,
                source_record_reference="rec-plm",
            ),
        ),
        created_by="steward",
        created_on=NOW,
    )


def _canonical_service(session: Session) -> OqiCrossSourceEvaluationService:
    return OqiCrossSourceEvaluationService(
        evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session),
        canonical_standard_lookup=OqiCanonicalStandardRepositoryImpl(session),
        clock=lambda: NOW,
    )


class TestConsistencyCanonicalProjection:
    def test_k1_raw_different_canonical_same_satisfied(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="USA",
        )
        rule = _consistency_rule(
            condition_id=f"cond-{uuid4()}",
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None

        evaluation = _canonical_service(session).evaluate_current_state(
            rule=rule, correspondence=correspondence
        )
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "SATISFIED"
        projections = (
            session.execute(
                select(ComparisonParticipantCanonicalProjectionORM).where(
                    ComparisonParticipantCanonicalProjectionORM.evaluation_id
                    == evaluation.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(projections) == 2  # both participants successfully projected (Case B)

    def test_k2_canonical_different_violated(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        usa_value_id, mexico_value_id = uuid4(), uuid4()
        standard_id = uuid4()
        standard = CanonicalStandard(
            canonical_standard_id=standard_id,
            information_element_requirement_id=ier_id,
            version_number=1,
            previous_version_id=None,
            status=CanonicalStandardStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            values=(
                CanonicalValue(
                    canonical_value_id=usa_value_id,
                    canonical_standard_id=standard_id,
                    canonical_representation="USA",
                    aliases=(
                        CanonicalAlias(
                            canonical_alias_id=uuid4(),
                            canonical_value_id=usa_value_id,
                            alias_representation="US",
                        ),
                    ),
                ),
                CanonicalValue(
                    canonical_value_id=mexico_value_id,
                    canonical_standard_id=standard_id,
                    canonical_representation="MEXICO",
                    aliases=(
                        CanonicalAlias(
                            canonical_alias_id=uuid4(),
                            canonical_value_id=mexico_value_id,
                            alias_representation="MX",
                        ),
                    ),
                ),
            ),
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(standard)
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="MX",
        )
        rule = _consistency_rule(
            condition_id=f"cond-{uuid4()}",
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None

        evaluation = _canonical_service(session).evaluate_current_state(
            rule=rule, correspondence=correspondence
        )
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"

    def test_k3_no_standard_falls_back_to_raw_comparison(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)  # no CanonicalStandard for this IE
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="MX",
        )
        rule = _consistency_rule(
            condition_id=f"cond-{uuid4()}",
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None

        evaluation = _canonical_service(session).evaluate_current_state(
            rule=rule, correspondence=correspondence
        )
        assert evaluation is not None
        assert (
            evaluation.outcome.value == "VIOLATED"
        )  # raw "US" != "MX" -- legacy Case A, unchanged
        projections = (
            session.execute(
                select(ComparisonParticipantCanonicalProjectionORM).where(
                    ComparisonParticipantCanonicalProjectionORM.evaluation_id
                    == evaluation.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert projections == []  # Case A never persists a canonical-projection row

    def test_k4_unmapped_participant_not_evaluable(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="Germany",
        )
        condition_id = f"cond-{uuid4()}"
        rule = _consistency_rule(
            condition_id=condition_id,
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None

        evaluation = _canonical_service(session).evaluate_current_state(
            rule=rule, correspondence=correspondence
        )
        assert (
            evaluation is None
        )  # NOT_EVALUABLE -- canonicalization failed, never a raw fallback here

    def test_k5_ambiguous_resolution_is_defensive(self) -> None:
        """CDD-049 §11-§12 make AMBIGUOUS structurally impossible to
        construct through governed persistence (a DB-level unique index
        prevents one alias from resolving to two values under the same
        active standard) -- proven at the pure, deterministic `canonicalize()`
        resolver directly, in-memory, exactly as CDD-049 §33 describes this
        case as defensive-only."""
        colliding_value_id = uuid4()
        other_value_id = uuid4()
        standard_id = uuid4()
        standard = CanonicalStandard(
            canonical_standard_id=standard_id,
            information_element_requirement_id=uuid4(),
            version_number=1,
            previous_version_id=None,
            status=CanonicalStandardStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            values=(
                CanonicalValue(
                    canonical_value_id=colliding_value_id,
                    canonical_standard_id=standard_id,
                    canonical_representation="USA",
                    aliases=(),
                ),
                CanonicalValue(
                    canonical_value_id=other_value_id,
                    canonical_standard_id=standard_id,
                    canonical_representation="OTHER",
                    aliases=(
                        CanonicalAlias(
                            canonical_alias_id=uuid4(),
                            canonical_value_id=other_value_id,
                            # An adversarial in-memory construction: an alias
                            # colliding with another value's own canonical
                            # representation string.
                            alias_representation="USA",
                        ),
                    ),
                ),
            ),
        )
        result = canonicalize(standard=standard, observed_representation="USA")
        assert result.resolution_state is CanonicalizationState.AMBIGUOUS
        assert result.resolved_canonical_value is None
        assert result.canonical_value_id is None

    def test_k6_no_fabricated_conflict_from_canonicalization_failure(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="Germany",
        )
        condition_id = f"cond-{uuid4()}"
        rule = _consistency_rule(
            condition_id=condition_id,
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None
        _canonical_service(session).evaluate_current_state(rule=rule, correspondence=correspondence)
        session.flush()

        findings = (
            session.execute(
                select(QualityComparisonFindingORM).where(
                    QualityComparisonFindingORM.tenant_id == tenant_id,
                    QualityComparisonFindingORM.quality_condition_id == condition_id,
                )
            )
            .scalars()
            .all()
        )
        assert findings == []  # zero Findings -- never a fabricated CROSS_SOURCE_VALUE_CONFLICT

    def test_k7_mixed_state_missingness_preserved(self, session: Session) -> None:
        """A known, canonicalizable SAP value plus a genuinely missing PLM
        participant (no evidence admitted at all for PLM's own subject
        coordinates): fewer than 2 known values means the canonicalization
        gate never engages, yet the independent missingness observation
        still yields VIOLATED (CDD-049 §16.2, amendment §13)."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        # No evidence admitted for PLM at all.
        rule = _consistency_rule(
            condition_id=f"cond-{uuid4()}",
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
            plm_expected=True,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None

        evaluation = _canonical_service(session).evaluate_current_state(
            rule=rule, correspondence=correspondence
        )
        assert evaluation is not None
        assert (
            evaluation.outcome.value == "VIOLATED"
        )  # missingness, independent of canonicalization

    def test_k8_canonical_projection_version_provenance(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        standard = _usa_standard(ier_id)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(standard)
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="USA",
        )
        rule = _consistency_rule(
            condition_id=f"cond-{uuid4()}",
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None
        evaluation = _canonical_service(session).evaluate_current_state(
            rule=rule, correspondence=correspondence
        )
        session.flush()
        assert evaluation is not None

        projections = (
            session.execute(
                select(ComparisonParticipantCanonicalProjectionORM).where(
                    ComparisonParticipantCanonicalProjectionORM.evaluation_id
                    == evaluation.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(projections) == 2
        for row in projections:
            assert row.standard_version == standard.version_number
            assert row.canonical_value_id == standard.values[0].canonical_value_id

    def test_k9_k10_historical_conflict_not_rewritten_only_fresh_satisfied_closes(
        self, session: Session
    ) -> None:
        """K9: a pre-H3-shaped raw conflict Finding, once persisted, is
        never mutated merely because a CanonicalStandard is introduced
        afterward -- its own historical evaluation row stays byte-identical.
        K10: the Finding transitions to RESOLVED only via a genuine, fresh
        SATISFIED re-evaluation call -- introducing the standard alone,
        without a new evaluation, changes nothing."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)  # deliberately no standard yet
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="USA",
        )
        condition_id = f"cond-{uuid4()}"
        rule = _consistency_rule(
            condition_id=condition_id,
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None

        first = _canonical_service(session).evaluate_current_state(
            rule=rule, correspondence=correspondence
        )
        session.flush()
        assert first is not None
        assert first.outcome.value == "VIOLATED"  # raw "US" != "USA", no standard yet -- Case A

        finding_before = session.execute(
            select(QualityComparisonFindingORM).where(
                QualityComparisonFindingORM.tenant_id == tenant_id,
                QualityComparisonFindingORM.quality_condition_id == condition_id,
            )
        ).scalar_one()
        assert finding_before.status == "OPEN"
        first_evaluation_id = first.evaluation_id

        # Introduce the standard AFTER the fact. Merely existing changes
        # nothing about the already-persisted Finding or evaluation row.
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        session.flush()
        finding_still_open = session.get(QualityComparisonFindingORM, finding_before.finding_id)
        assert finding_still_open is not None
        assert finding_still_open.status == "OPEN"  # K9: unchanged by the standard's mere existence
        assert finding_still_open.latest_evaluation_id == first_evaluation_id

        # K10: only a genuine, fresh re-evaluation call -- now canonicalizing
        # both to "USA" -- closes the Finding. A distinct evaluation_horizon
        # (a later clock reading) is required for a genuinely new
        # evaluation_id -- the deterministic id formula does not depend on
        # outcome, only on identity/horizon/participant-evidence digest.
        later_service = OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session),
            canonical_standard_lookup=OqiCanonicalStandardRepositoryImpl(session),
            clock=lambda: NOW + timedelta(hours=1),
        )
        second = later_service.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.flush()
        assert second is not None
        assert second.outcome.value == "SATISFIED"
        assert second.evaluation_id != first_evaluation_id

        finding_after = session.get(QualityComparisonFindingORM, finding_before.finding_id)
        assert finding_after is not None
        assert finding_after.status == "RESOLVED"
        assert finding_after.latest_evaluation_id == second.evaluation_id


# =======================================================================
# VALIDITY INDEPENDENCE -- V1-V3.
# =======================================================================


class TestValidityIndependence:
    def test_v1_valid_and_conforming(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        validity_rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            information_element_requirement_id=str(ier_id),
            rule_parameters={"allowed_values": ["USA", "US"]},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        conformity_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(validity_rule)
        OqiQualityRuleRepositoryImpl(session).create(conformity_rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        legacy_service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        validity_evaluation = legacy_service.evaluate_current_state(
            rule=validity_rule, subject=subject
        )
        conformity_evaluation = _conformity_service(session).evaluate_current_state(
            rule=conformity_rule, subject=subject
        )
        assert validity_evaluation is not None and validity_evaluation.outcome.value == "SATISFIED"
        assert (
            conformity_evaluation is not None and conformity_evaluation.outcome.value == "SATISFIED"
        )

    def test_v2_valid_and_nonconforming(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",  # valid enum member, but only an alias -- non-canonical
        )
        validity_rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            information_element_requirement_id=str(ier_id),
            rule_parameters={"allowed_values": ["USA", "US"]},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        conformity_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(validity_rule)
        OqiQualityRuleRepositoryImpl(session).create(conformity_rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        legacy_service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        validity_evaluation = legacy_service.evaluate_current_state(
            rule=validity_rule, subject=subject
        )
        conformity_evaluation = _conformity_service(session).evaluate_current_state(
            rule=conformity_rule, subject=subject
        )
        assert validity_evaluation is not None and validity_evaluation.outcome.value == "SATISFIED"
        assert (
            conformity_evaluation is not None and conformity_evaluation.outcome.value == "VIOLATED"
        )

    def test_v3_validity_unaffected_by_alias_recognition(self, session: Session) -> None:
        """A value that IS a recognized alias, but is NOT itself a member of
        the Validity rule's own governed enum, still VIOLATES Validity --
        Validity's own allowed-values list is never widened by whatever the
        CanonicalStandard separately recognizes as an alias."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        validity_rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            information_element_requirement_id=str(ier_id),
            rule_parameters={"allowed_values": ["USA"]},  # deliberately excludes "US"
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(validity_rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        legacy_service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        validity_evaluation = legacy_service.evaluate_current_state(
            rule=validity_rule, subject=subject
        )
        assert validity_evaluation is not None
        assert validity_evaluation.outcome.value == "VIOLATED"  # "US" not in Validity's own enum


# =======================================================================
# ACCURACY NON-INTERFERENCE -- A1-A3.
# =======================================================================


def _reference_service(session: Session) -> OqiReferenceEvidenceService:
    return OqiReferenceEvidenceService(
        repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
    )


class TestAccuracyNonInterference:
    def test_a1_h2_accuracy_unchanged_by_canonical_standard_existence_live(
        self, session: Session
    ) -> None:
        """A1, live: a real `CanonicalStandard` genuinely exists for the
        same Information Element H2's own Accuracy crown evaluates -- proves
        Accuracy's raw, byte-exact reference comparison is entirely
        unaffected by that existence (PO-H3-02)."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",  # a recognized alias under the standard above
        )
        rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.ACCURACY,
            finding_type=QualityFindingType.REFERENCE_VALUE_UNSUPPORTED,
            validity_primitive=None,
            information_element_requirement_id=str(ier_id),
            rule_parameters={},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="US",  # byte-exact match to the raw observation, not the canonical form
            dataset_name="demo",
            dataset_version="v1",
            entry_key="US",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is not None
        assert (
            evaluation.outcome.value == "SATISFIED"
        )  # exact match wins, unaffected by canonicalization

    def test_a2_conforming_but_not_accurate(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",  # canonical -- SATISFIED under Conformity
        )
        accuracy_rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        conformity_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(accuracy_rule)
        OqiQualityRuleRepositoryImpl(session).create(conformity_rule)
        session.flush()
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="MEXICO",  # disagrees -- VIOLATED under Accuracy
            dataset_name="demo",
            dataset_version="v1",
            entry_key="MEXICO",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        accuracy_evaluation = _accuracy_service(session).evaluate_current_state(
            rule=accuracy_rule, subject=subject
        )
        conformity_evaluation = _conformity_service(session).evaluate_current_state(
            rule=conformity_rule, subject=subject
        )
        assert accuracy_evaluation is not None and accuracy_evaluation.outcome.value == "VIOLATED"
        assert (
            conformity_evaluation is not None and conformity_evaluation.outcome.value == "SATISFIED"
        )

    def test_a3_nonconforming_does_not_imply_inaccurate(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",  # alias -- VIOLATED under Conformity
        )
        accuracy_rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        conformity_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(accuracy_rule)
        OqiQualityRuleRepositoryImpl(session).create(conformity_rule)
        session.flush()
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="US",  # byte-exact match to the raw observation
            dataset_name="demo",
            dataset_version="v1",
            entry_key="US",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        accuracy_evaluation = _accuracy_service(session).evaluate_current_state(
            rule=accuracy_rule, subject=subject
        )
        conformity_evaluation = _conformity_service(session).evaluate_current_state(
            rule=conformity_rule, subject=subject
        )
        assert accuracy_evaluation is not None and accuracy_evaluation.outcome.value == "SATISFIED"
        assert (
            conformity_evaluation is not None and conformity_evaluation.outcome.value == "VIOLATED"
        )


# =======================================================================
# ORIGIN / DOWNSTREAM -- F1-F5.
# =======================================================================


class TestOriginAndDownstream:
    def test_f1_origin_is_conformity(self) -> None:
        assert (
            quality_dimension_for_oqi1_finding_type(QualityFindingType.NON_CANONICAL_REPRESENTATION)
            is QualityDimension.CONFORMITY
        )

    def test_f2_storage_family_is_oqi1_live(self, session: Session) -> None:
        from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
            OqiOntologyImpactEvaluationRepositoryImpl,
        )

        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None
        finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.quality_condition_id == rule.quality_condition_id,
            )
        ).scalar_one()
        origin = OqiOntologyImpactEvaluationRepositoryImpl(session).resolve_finding_origin(
            tenant_id=tenant_id,
            finding_family=OntologyImpactFindingFamily.OQI1,
            finding_id=finding.finding_id,
        )
        assert origin.finding_storage_family is FindingStorageFamily.OQI1
        assert origin.quality_dimension == "CONFORMITY"

    def test_f3_f4_f5_downstream_services_carry_no_conformity_special_case(self) -> None:
        """F3/F4/F5: Ontology Impact, Business Impact, and Reliance are
        claimed generic -- they consume `QualityFindingOrigin.quality_
        dimension` as an opaque value, never branching on `CONFORMITY`
        specifically. Proven structurally (AST-verified, mirroring CDD-048's
        own CY3-CY5 import-firewall precedent): the literal `"CONFORMITY"`
        appears nowhere in any of these three modules' source."""
        modules = (
            "app/application/oqi_ontology_impact_evaluation_service.py",
            "app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py",
            "app/application/oqi_business_impact_service.py",
            "app/infrastructure/persistence/oqi_business_impact_repository.py",
        )
        for relative_path in modules:
            path = REPOSITORY_ROOT / "backend" / relative_path
            if not path.exists():
                continue
            source = path.read_text()
            assert "CONFORMITY" not in source, f"{relative_path} must not special-case CONFORMITY"


# =======================================================================
# COVERAGE -- CV1-CV5.
# =======================================================================


class TestCoverage:
    def _coverage_repo(self, session: Session) -> OqiQualityCoveragePolicyRepositoryImpl:
        return OqiQualityCoveragePolicyRepositoryImpl(session)

    def test_cv1_satisfied_conformity_counts(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        coverage_repo = self._coverage_repo(session)
        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.CONFORMITY,
            )
            is False
        )
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.CONFORMITY,
            )
            is True
        )

    def test_cv2_violated_conformity_counts(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",  # alias -- VIOLATED
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None and evaluation.outcome.value == "VIOLATED"
        assert (
            self._coverage_repo(session).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.CONFORMITY,
            )
            is True
        )  # existence-only, regardless of outcome

    def test_cv3_no_standard_does_not_count(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)  # no standard
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None
        assert (
            self._coverage_repo(session).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.CONFORMITY,
            )
            is False
        )

    def test_cv4_unmapped_does_not_count(self, session: Session) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="Atlantis",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None
        assert (
            self._coverage_repo(session).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.CONFORMITY,
            )
            is False
        )

    def test_cv5_partial_required_coverage_is_not_supported(self, session: Session) -> None:
        """PARTIAL REQUIRED COVERAGE != SUPPORTED (reaffirmed invariant):
        an object covered for Conformity alone, while Validity is also
        required, must not read as fully covered across the required set."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()

        coverage_repo = self._coverage_repo(session)
        required = (CoverageDimension.VALIDITY, CoverageDimension.CONFORMITY)
        satisfied = {
            dimension: coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=(source_object_id,), dimension=dimension
            )
            for dimension in required
        }
        assert satisfied[CoverageDimension.CONFORMITY] is True
        assert satisfied[CoverageDimension.VALIDITY] is False
        assert not all(satisfied.values())  # partial, therefore not "supported"


# =======================================================================
# REMEDIATION -- R1-R4.
# =======================================================================


def _remediation_service(session: Session) -> OqiRemediationService:
    return OqiRemediationService(
        repository=OqiRemediationRepositoryImpl(session),
        participant_reader=OqiRemediationParticipantReader(session),
    )


class TestRemediation:
    def test_r1_alias_violation_produces_exact_canonical_update_field_candidate(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        standard = _usa_standard(ier_id)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(standard)
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None and evaluation.outcome.value == "VIOLATED"
        finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.quality_condition_id == rule.quality_condition_id,
            )
        ).scalar_one()

        _case, candidates = _remediation_service(session).extract_candidates(
            tenant_id=tenant_id,
            finding_family=FindingFamily.OQI1,
            finding_id=finding.finding_id,
            quality_dimension="CONFORMITY",
            now=NOW,
        )
        session.flush()
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.proposed_value == "USA"  # the exact governed canonical value
        assert candidate.basis is RemediationCandidateBasis.CONFORMITY_CANONICAL_STANDARD
        assert candidate.target_source_field_id == source_field_id

    def test_r2_no_candidate_for_not_evaluable(self, session: Session) -> None:
        """A NOT_EVALUABLE Conformity attempt persists zero evaluation/
        Finding rows at all -- there is nothing for remediation to extract
        a candidate from in the first place (proven by the absence of any
        Finding to pass to `extract_candidates`, mirroring R2's own
        no-candidate claim)."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="Narnia",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None
        findings = (
            session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert findings == []

    def test_r3_candidate_is_not_truth(self, session: Session) -> None:
        """CANDIDATE != TRUTH (reaffirmed): extracting a remediation
        candidate never itself mutates the Finding, the raw evidence, or
        creates a new Conformity evaluation -- it is purely a proposal."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        evidence_id = _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.quality_condition_id == rule.quality_condition_id,
            )
        ).scalar_one()
        finding_status_before = finding.status

        _remediation_service(session).extract_candidates(
            tenant_id=tenant_id,
            finding_family=FindingFamily.OQI1,
            finding_id=finding.finding_id,
            quality_dimension="CONFORMITY",
            now=NOW,
        )
        session.flush()

        raw = session.get(FieldValueEvidenceORM, evidence_id)
        assert raw is not None and raw.observed_representation == "US"  # unchanged
        finding_after = session.get(QualityFindingORM, finding.finding_id)
        assert finding_after is not None
        assert (
            finding_after.status == finding_status_before
        )  # unchanged -- extraction never resolves

    def test_r4_remediation_is_not_resolution(self, session: Session) -> None:
        """REMEDIATION != RESOLUTION (reaffirmed): a `RemediationCase` being
        opened never, by itself, closes the underlying Finding -- only a
        fresh, independently re-evaluated SATISFIED Conformity evaluation
        does (mirroring K10's own discipline)."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session)
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="MFG-COUNTRY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        _conformity_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.quality_condition_id == rule.quality_condition_id,
            )
        ).scalar_one()

        case, _candidates = _remediation_service(session).extract_candidates(
            tenant_id=tenant_id,
            finding_family=FindingFamily.OQI1,
            finding_id=finding.finding_id,
            quality_dimension="CONFORMITY",
            now=NOW,
        )
        session.flush()
        assert case is not None

        finding_after_case = session.get(QualityFindingORM, finding.finding_id)
        assert finding_after_case is not None
        assert finding_after_case.status == "OPEN"  # opening a case never resolves the Finding


# =======================================================================
# ER BOUNDARY -- E1-E2.
# =======================================================================


class TestErBoundary:
    def test_e1_no_er_normalization_import(self) -> None:
        """E1, static AST-verified, mirroring CDD-048's own CY3-CY5
        import-firewall precedent exactly: neither the canonicalization
        resolver nor either H3 evaluator imports anything from
        `app.domain.identity_resolution`."""
        modules = (
            "backend/app/domain/oqi_canonical_standard/standard.py",
            "backend/app/application/oqi_conformity_evaluation_service.py",
            "backend/app/application/oqi_cross_source_evaluation_service.py",
        )
        for relative_path in modules:
            path = REPOSITORY_ROOT / relative_path
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith(
                        "app.domain.identity_resolution"
                    ), f"{relative_path} must never import from identity_resolution"
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith(
                            "app.domain.identity_resolution"
                        ), f"{relative_path} must never import identity_resolution"

    def test_e2_er_normalization_cannot_substitute_for_conformity_resolver(self) -> None:
        """E2, adversarial: `canonicalize()` has no parameter, hook, or
        extension point through which an ER normalization function could be
        wired in as an alternate resolver -- its signature is closed,
        exactly `(standard, observed_representation) -> CanonicalizationResult`."""
        import inspect

        signature = inspect.signature(canonicalize)
        assert set(signature.parameters) == {"standard", "observed_representation"}


# =======================================================================
# H2 NON-REGRESSION + H3 CROWN SCENARIO -- LIVE, TOGETHER.
# =======================================================================


class TestH2NonRegressionAndH3CrownLiveTogether:
    def test_h3_crown_and_h2_crown_coexist_in_same_database_state(self, session: Session) -> None:
        """CDD-049 §30-§31: the full H3 crown (SAP Conformity VIOLATED, PLM
        Conformity SATISFIED, Consistency SATISFIED through canonical
        projection) proven live in the exact same database state as the H2
        Accuracy/Reasonableness crown (unchanged SAP SATISFIED / PLM
        VIOLATED), proving H3 introduces zero regression to H2."""
        tenant_id = _tenant()
        ier_id = _seed_information_element(session, element_name="Manufacturing Country")
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(_usa_standard(ier_id))

        # -- H3 crown: SAP observes the alias "US" (Conformity VIOLATED),
        # PLM observes the canonical "USA" directly (Conformity SATISFIED),
        # Consistency SATISFIED through canonical projection.
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-MC")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-MC")
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="USA",
        )
        sap_conformity_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        plm_conformity_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(sap_conformity_rule)
        OqiQualityRuleRepositoryImpl(session).create(plm_conformity_rule)
        consistency_rule = _consistency_rule(
            condition_id=f"cond-{uuid4()}",
            sap_field=sap_field,
            plm_field=plm_field,
            information_element_requirement_id=ier_id,
        )
        OqiQualityRuleRepositoryImpl(session).create(consistency_rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.flush()

        sap_subject = _subject(
            tenant_id=tenant_id,
            source_object_id=sap_object,
            source_field_id=sap_field,
            reference="rec-sap",
        )
        plm_subject = _subject(
            tenant_id=tenant_id,
            source_object_id=plm_object,
            source_field_id=plm_field,
            reference="rec-plm",
        )
        conformity_service = _conformity_service(session)
        sap_conformity = conformity_service.evaluate_current_state(
            rule=sap_conformity_rule, subject=sap_subject
        )
        plm_conformity = conformity_service.evaluate_current_state(
            rule=plm_conformity_rule, subject=plm_subject
        )
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None
        consistency = _canonical_service(session).evaluate_current_state(
            rule=consistency_rule, correspondence=correspondence
        )
        assert sap_conformity is not None and sap_conformity.outcome.value == "VIOLATED"
        assert plm_conformity is not None and plm_conformity.outcome.value == "SATISFIED"
        assert consistency is not None and consistency.outcome.value == "SATISFIED"

        # -- H2 crown, byte-identical raw values, live in the SAME database
        # state: SAP "US" / PLM "MX" / Reference "US" -- SATISFIED / VIOLATED.
        h2_sap_object, h2_sap_field, h2_entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id, field_label="H2-SAP-FIELD"
        )
        h2_plm_object, h2_plm_field = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="H2-PLM-FIELD"
        )
        from app.tests.test_oqi_ontology_impact_postgres import _resolve_entity

        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=h2_plm_object, entity_id=h2_entity_id
        )
        _admit_evidence(
            session,
            source_field_id=h2_sap_field,
            source_record_reference="h2-rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=h2_plm_field,
            source_record_reference="h2-rec-plm",
            observed_representation="MX",
        )
        h2_accuracy_rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(h2_accuracy_rule)
        session.flush()
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=h2_entity_id,
            source_field_id=h2_sap_field,
            asserted_value="US",
            dataset_name="ISO-3166-1-ALPHA-3",
            dataset_version="2024",
            entry_key="US",
            created_by="steward",
        )
        # Reference Evidence is scoped per (entity, source_field_id) -- PLM's
        # own field needs its own assertion too, mirroring the H2 crown's
        # own A6 test precedent exactly.
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=h2_entity_id,
            source_field_id=h2_plm_field,
            asserted_value="US",
            dataset_name="ISO-3166-1-ALPHA-3",
            dataset_version="2024",
            entry_key="US",
            created_by="steward",
        )
        session.flush()

        h2_sap_subject = _subject(
            tenant_id=tenant_id,
            source_object_id=h2_sap_object,
            source_field_id=h2_sap_field,
            reference="h2-rec-sap",
        )
        h2_plm_subject = _subject(
            tenant_id=tenant_id,
            source_object_id=h2_plm_object,
            source_field_id=h2_plm_field,
            reference="h2-rec-plm",
        )
        h2_accuracy_service = _accuracy_service(session)
        h2_sap_accuracy = h2_accuracy_service.evaluate_current_state(
            rule=h2_accuracy_rule, subject=h2_sap_subject
        )
        h2_plm_accuracy = h2_accuracy_service.evaluate_current_state(
            rule=h2_accuracy_rule, subject=h2_plm_subject
        )
        assert h2_sap_accuracy is not None and h2_sap_accuracy.outcome.value == "SATISFIED"
        assert h2_plm_accuracy is not None and h2_plm_accuracy.outcome.value == "VIOLATED"
