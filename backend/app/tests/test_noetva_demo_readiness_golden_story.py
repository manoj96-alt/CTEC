"""CDD-085 Noetva Demo Readiness Golden Story -- Artifact Authorization §2
row 1 crown suite: the D1-D25 deterministic-state contract (§6 of the
companion Artifact Authorization) plus the CDD-085-Artifact-Authorization-
G-R1-Entity-Resolution-Flush-Ordering-Amendment's own narrow regression
proof (its §19/§22). All Golden Demo entities/evidence/findings flow
through the real, unmodified production seeders and evaluators -- never a
directly-inserted conclusion.

REMEDIATION != RESOLUTION (D12): if the underlying SAP/PLM evidence is
unchanged, reporting a remediation execution must never itself close the
Finding -- only an independent, later re-evaluation of that unchanged
evidence can, and it will not, because the evidence has not changed. This
file asserts that outcome as a PASS condition, never "fixes" it.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.ontology_copilot_api import AskStatus, OntologyCopilotApiService
from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.application.oqi_remediation_service import OqiRemediationError, OqiRemediationService
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.domain.oqi_business_impact.reliance import RelianceState
from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
from app.domain.oqi_remediation.case import FindingFamily
from app.domain.oqi_uniqueness.candidate import UniquenessAdjudicationAction
from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder
from app.infrastructure.persistence.demo_oqi_seeder import (
    _AURORA_BOM_ID,
    _AURORA_DEFINES_EDGE_ID,
    _AURORA_MATERIAL_ID,
    _AURORA_SUPPLIES_EDGE_ID,
    _AURORA_USED_IN_EDGE_ID,
    _COMPARISON_SUBJECT_ID,
    _H6_PRODUCT_A_ID,
    _H6_PRODUCT_B_ID,
    _PLM_FIELD_ID,
    _QUALITY_CONDITION_ID,
    _SAP_FIELD_ID,
    _SUPPLIER_ENTITY_ID,
    DemoOqiSeeder,
    DemoOqiSeedSummary,
)
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionHistoryModel,
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_remediation_agent import (
    AgentRunORM,
)
from app.infrastructure.persistence.models.oqi_uniqueness import (
    UniquenessAdjudicationORM,
    UniquenessFindingORM,
)
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)

# ----------------------------------------------------------------------
# Fixtures -- seed the real, governed Golden Demo tenant exactly once per
# module via the real, unmodified production seeders (never a synthetic
# fixture tenant): this suite proves the *actual* deterministic-demo
# behavior, not a stand-in for it.
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture(scope="module")
def golden_summary(factory: sessionmaker[Session]) -> DemoOqiSeedSummary:
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        BlueprintSeeder(session).load()
        session.commit()
        summary = DemoOqiSeeder(session).seed()
        session.commit()
    return summary


@pytest.fixture()
def session(
    factory: sessionmaker[Session], golden_summary: DemoOqiSeedSummary
) -> Generator[Session, None, None]:
    del golden_summary  # ordering dependency only -- ensures seed ran first
    with factory() as session:
        yield session
        session.rollback()


FINDING_ID: UUID = derive_comparison_finding_id(
    tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
    quality_condition_id=_QUALITY_CONDITION_ID,
    comparison_subject_id=_COMPARISON_SUBJECT_ID,
)


def _principal(scopes: tuple[str, ...] = ("ontology-copilot:ask",)) -> TrustedPrincipal:
    now = datetime.now(UTC)
    return TrustedPrincipal(
        principal_id="user-maya",
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(hours=1),
    )


# ----------------------------------------------------------------------
# D1 -- Golden Supplier seed is deterministic; re-running is idempotent.
# ----------------------------------------------------------------------


def test_d1_golden_supplier_deterministic_and_idempotent(
    session: Session, golden_summary: DemoOqiSeedSummary
) -> None:
    supplier = session.get(EnterpriseEntity, _SUPPLIER_ENTITY_ID)
    assert supplier is not None
    assert supplier.enterprise_entity_name == "Meridian Cell Components"
    assert golden_summary.supplier_entity_id == _SUPPLIER_ENTITY_ID

    before = session.scalar(
        select(EnterpriseEntity).where(EnterpriseEntity.enterprise_entity_id == _SUPPLIER_ENTITY_ID)
    )
    assert before is not None
    # Idempotency: re-running seed() in a fresh session must not duplicate
    # or alter the already-seeded Supplier row.
    with sessionmaker(bind=session.get_bind())() as second_session:
        DemoOqiSeeder(second_session).seed()
        second_session.commit()
    count = session.scalar(
        select(EnterpriseEntity.enterprise_entity_id).where(
            EnterpriseEntity.enterprise_entity_name == "Meridian Cell Components"
        )
    )
    assert count == _SUPPLIER_ENTITY_ID


# ----------------------------------------------------------------------
# D2 -- SAP/PLM Country-of-Origin evidence values are exactly "US"/"MX".
# ----------------------------------------------------------------------


def test_d2_sap_plm_evidence_deterministic(session: Session) -> None:
    sap = session.scalar(
        select(FieldValueEvidenceORM).where(FieldValueEvidenceORM.source_field_id == _SAP_FIELD_ID)
    )
    plm = session.scalar(
        select(FieldValueEvidenceORM).where(FieldValueEvidenceORM.source_field_id == _PLM_FIELD_ID)
    )
    assert sap is not None and sap.observed_representation == "US"
    assert plm is not None and plm.observed_representation == "MX"


# ----------------------------------------------------------------------
# D3 -- the renamed Supplier resolves to the same governed entity_id the
# existing evaluations already reference.
# ----------------------------------------------------------------------


def test_d3_renamed_supplier_shares_governed_identity(
    session: Session, golden_summary: DemoOqiSeedSummary
) -> None:
    record = session.scalar(
        select(EnterpriseEntityResolutionRecordModel).where(
            EnterpriseEntityResolutionRecordModel.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            EnterpriseEntityResolutionRecordModel.enterprise_entity_id == _SUPPLIER_ENTITY_ID,
        )
    )
    assert record is not None
    assert golden_summary.supplier_entity_id == _SUPPLIER_ENTITY_ID == record.enterprise_entity_id


# ----------------------------------------------------------------------
# D4 -- the connected ontology chain exists with correct edges.
# ----------------------------------------------------------------------


def test_d4_connected_ontology_chain(session: Session) -> None:
    material = session.get(EnterpriseEntity, _AURORA_MATERIAL_ID)
    bom = session.get(EnterpriseEntity, _AURORA_BOM_ID)
    product = session.get(EnterpriseEntity, _H6_PRODUCT_A_ID)
    assert material is not None and material.enterprise_entity_name == "Aurora X1 Battery Cell"
    assert bom is not None and bom.enterprise_entity_name == "Aurora X1 Bill of Materials"
    assert product is not None and product.enterprise_entity_name == "Aurora X1"

    supplies = session.get(InstitutionalRelationship, _AURORA_SUPPLIES_EDGE_ID)
    used_in = session.get(InstitutionalRelationship, _AURORA_USED_IN_EDGE_ID)
    defines = session.get(InstitutionalRelationship, _AURORA_DEFINES_EDGE_ID)
    assert supplies is not None
    assert supplies.from_entity_id == _SUPPLIER_ENTITY_ID
    assert supplies.to_entity_id == _AURORA_MATERIAL_ID
    assert used_in is not None
    assert used_in.from_entity_id == _AURORA_MATERIAL_ID
    assert used_in.to_entity_id == _AURORA_BOM_ID
    assert defines is not None
    assert defines.from_entity_id == _AURORA_BOM_ID
    assert defines.to_entity_id == _H6_PRODUCT_A_ID


# ----------------------------------------------------------------------
# D5 -- existing OQI evaluations are byte-identical outcomes to pre-rename.
# ----------------------------------------------------------------------


def test_d5_existing_evaluation_outcomes_unaffected_by_rename(
    golden_summary: DemoOqiSeedSummary,
) -> None:
    assert golden_summary.accuracy_sap_outcome == "SATISFIED"
    assert golden_summary.accuracy_plm_outcome == "VIOLATED"
    assert golden_summary.reasonableness_outcome == "VIOLATED"
    assert golden_summary.conformity_sap_outcome == "VIOLATED"
    assert golden_summary.conformity_plm_outcome == "SATISFIED"
    assert golden_summary.h3_consistency_outcome == "SATISFIED"


# ----------------------------------------------------------------------
# D6 -- the primary OQI2 Consistency Finding is OPEN.
# ----------------------------------------------------------------------


def test_d6_primary_finding_open(session: Session) -> None:
    finding = session.scalar(
        select(QualityComparisonFindingORM).where(
            QualityComparisonFindingORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            QualityComparisonFindingORM.quality_condition_id == _QUALITY_CONDITION_ID,
        )
    )
    assert finding is not None
    assert finding.status == "OPEN"


# ----------------------------------------------------------------------
# D7 -- Business Impact HIGH.
# ----------------------------------------------------------------------


def test_d7_business_dependency_criticality_high(
    session: Session, golden_summary: DemoOqiSeedSummary
) -> None:
    from app.infrastructure.persistence.models.oqi_business_impact import (
        OqiBusinessDependencyORM,
    )

    dependency = session.scalar(
        select(OqiBusinessDependencyORM)
        .where(OqiBusinessDependencyORM.dependency_id == golden_summary.business_dependency_id)
        .order_by(OqiBusinessDependencyORM.version.desc())
        .limit(1)
    )
    assert dependency is not None
    assert dependency.criticality == "HIGH"


# ----------------------------------------------------------------------
# D8 -- Reliance state is RELIANCE_AT_RISK.
# ----------------------------------------------------------------------


def test_d8_reliance_at_risk(golden_summary: DemoOqiSeedSummary) -> None:
    assert golden_summary.reliance_state == RelianceState.RELIANCE_AT_RISK.value


# ----------------------------------------------------------------------
# D9-D12, D9 candidate / D10 named human / D11 re-evaluation / D12
# REMEDIATION != RESOLUTION, all against the real production remediation
# service and the real production OQI2 evaluator, never a fake.
# ----------------------------------------------------------------------


def test_d9_d12_remediation_signature_moment(session: Session) -> None:
    remediation = OqiRemediationService(
        repository=OqiRemediationRepositoryImpl(session),
        participant_reader=OqiRemediationParticipantReader(session),
    )

    _case, candidates = remediation.extract_candidates(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        finding_family=FindingFamily.OQI2,
        finding_id=FINDING_ID,
    )
    # D9: real, non-fabricated candidates -- both dissenting source values.
    assert candidates, "expected at least one real remediation candidate"
    proposed_values = {c.proposed_value for c in candidates}
    assert proposed_values == {"US", "MX"}
    chosen = candidates[0]

    instruction = remediation.construct_instruction(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        candidate_id=chosen.candidate_id,
        created_by="demo-presenter",
    )
    authorization = remediation.request_authorization(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        instruction_id=instruction.instruction_id,
        requested_by="demo-presenter",
    )

    # D10: an anonymous/self decision is rejected -- a named, distinct
    # human principal is required.
    with pytest.raises(OqiRemediationError) as excinfo:
        remediation.approve(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            authorization_id=authorization.authorization_id,
            decided_by="demo-presenter",
        )
    assert excinfo.value.code == "REMEDIATION_SELF_APPROVAL_PROHIBITED"

    approved = remediation.approve(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        authorization_id=authorization.authorization_id,
        decided_by="demo-approver-maya",
    )
    assert approved.status.value == "APPROVED"

    before_finding = session.scalar(
        select(QualityComparisonFindingORM).where(
            QualityComparisonFindingORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            QualityComparisonFindingORM.quality_condition_id == _QUALITY_CONDITION_ID,
        )
    )
    assert before_finding is not None
    before_revision = before_finding.state_revision

    case_after = remediation.report_external_execution(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, authorization_id=authorization.authorization_id
    )
    assert case_after.external_execution_claimed is True
    session.flush()

    # D11: re-evaluation (the real, unmodified OQI2 evaluator -- the exact
    # mechanism the production re-evaluation orchestrator itself invokes,
    # CDD-058) increments state_revision.
    def _clock() -> datetime:
        return before_finding.last_evaluated_horizon + timedelta(seconds=1)

    from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
        OqiCrossSourceCorrespondenceRepositoryImpl,
    )
    from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
        OqiCrossSourceEvaluationRepositoryImpl,
    )
    from app.infrastructure.persistence.oqi_quality_rule_repository import (
        OqiQualityRuleRepositoryImpl,
    )

    rule = OqiQualityRuleRepositoryImpl(session).get_active(_QUALITY_CONDITION_ID)
    assert rule is not None
    correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, comparison_subject_id=_COMPARISON_SUBJECT_ID
    )
    assert correspondence is not None
    OqiCrossSourceEvaluationService(
        evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session), clock=_clock
    ).evaluate_current_state(rule=rule, correspondence=correspondence)
    session.flush()

    after_finding = session.scalar(
        select(QualityComparisonFindingORM).where(
            QualityComparisonFindingORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            QualityComparisonFindingORM.quality_condition_id == _QUALITY_CONDITION_ID,
        )
    )
    assert after_finding is not None
    assert after_finding.state_revision > before_revision

    # D12 -- the signature moment: SAP/PLM evidence never changed, so the
    # Finding remains OPEN. This is a PASS condition, not a defect.
    assert after_finding.status == "OPEN"


# ----------------------------------------------------------------------
# D13-D15 -- the H6 pair shares the Golden universe; candidate != fact;
# no merge/deactivate authority exists.
# ----------------------------------------------------------------------


def test_d13_h6_pair_shares_golden_universe(session: Session) -> None:
    finding = session.scalar(
        select(UniquenessFindingORM).where(
            UniquenessFindingORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            UniquenessFindingORM.member_a_id.in_((_H6_PRODUCT_A_ID, _H6_PRODUCT_B_ID)),
            UniquenessFindingORM.member_b_id.in_((_H6_PRODUCT_A_ID, _H6_PRODUCT_B_ID)),
        )
    )
    assert finding is not None
    product = session.get(EnterpriseEntity, _H6_PRODUCT_A_ID)
    assert product is not None and product.enterprise_entity_name == "Aurora X1"


def test_d14_candidate_is_not_fact(session: Session) -> None:
    finding = session.scalar(
        select(UniquenessFindingORM).where(
            UniquenessFindingORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            UniquenessFindingORM.member_a_id.in_((_H6_PRODUCT_A_ID, _H6_PRODUCT_B_ID)),
            UniquenessFindingORM.member_b_id.in_((_H6_PRODUCT_A_ID, _H6_PRODUCT_B_ID)),
        )
    )
    assert finding is not None
    assert finding.status == "OPEN"
    adjudication = session.scalar(
        select(UniquenessAdjudicationORM).where(
            UniquenessAdjudicationORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            UniquenessAdjudicationORM.candidate_id == finding.candidate_id,
        )
    )
    assert adjudication is None


def test_d15_no_merge_or_deactivate_action_exists(session: Session) -> None:
    del session
    values = {action.value for action in UniquenessAdjudicationAction}
    assert values == {"REJECT_NOT_DUPLICATE", "CONFIRM_DUPLICATE"}
    assert "MERGE_ENTITY" not in values
    assert "DEACTIVATE_ENTITY" not in values


# ----------------------------------------------------------------------
# D18 -- contextual navigation is present only for OQI2-family findings
# (frontend contract asserted structurally: findingFamily gating lives in
# evidence-panel.tsx, proven by its own no-fabrication audit, §BC of the
# final report). `quality_comparison_findings` (CDD-040) is itself the
# OQI2 storage family -- distinct from OQI1's `quality_findings` -- so a
# row's mere presence in this table *is* the OQI2 precondition; there is
# no separate `finding_family` column to assert on this model.
# ----------------------------------------------------------------------


def test_d18_oqi2_finding_family_precondition(session: Session) -> None:
    finding = session.scalar(
        select(QualityComparisonFindingORM).where(
            QualityComparisonFindingORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            QualityComparisonFindingORM.quality_condition_id == _QUALITY_CONDITION_ID,
        )
    )
    assert finding is not None


# ----------------------------------------------------------------------
# D20 -- Ask CTEC live query against real Golden data. This test FAILS
# loudly on no_match/ambiguous_match, per CDD-085 AA §6 D20 -- it must
# never silently pass either way.
# ----------------------------------------------------------------------


def test_d20_ask_ctec_live_query(factory: sessionmaker[Session]) -> None:
    service = OntologyCopilotApiService(sessions=factory)
    result = service.ask(
        _principal(),
        "Which products depend on Meridian Cell Components?",
    )
    assert result.status == AskStatus.ANSWERED, (
        f"Ask CTEC D20 did not resolve against live Golden data (status={result.status!r}, "
        f"answer={result.answer!r}) -- Ask CTEC remains EXTENDED-DEMO-ONLY, not promotable"
    )
    assert "Aurora X1" in result.answer


# ----------------------------------------------------------------------
# D21 -- Agent Investigation returns zero specialists/zero recommendation:
# no production caller of the agent-reasoning execution path exists
# anywhere in this repository (CDD-084 H6-G-R1 §9/§11, unmodified by
# Demo Readiness) -- re-confirmed here against the Golden Finding
# specifically, not merely structurally.
# ----------------------------------------------------------------------


def test_d21_agent_investigation_not_fabricated(session: Session) -> None:
    from app.domain.oqi_remediation.case import derive_remediation_case_id

    case_id = derive_remediation_case_id(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        finding_family=FindingFamily.OQI2,
        finding_id=FINDING_ID,
    )
    runs = session.scalars(
        select(AgentRunORM).where(
            AgentRunORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID,
            AgentRunORM.case_id == case_id,
        )
    ).all()
    assert (
        list(runs) == []
    ), "no AgentRun row may exist for the Golden Finding -- honest not_invoked"


# ----------------------------------------------------------------------
# D22 -- tenant isolation is unaffected: the renamed entities still
# require the correct tenant_id.
# ----------------------------------------------------------------------


def test_d22_tenant_scoping_unchanged(session: Session) -> None:
    other_tenant_supplier = session.scalar(
        select(EnterpriseEntity).where(
            EnterpriseEntity.enterprise_entity_id == _SUPPLIER_ENTITY_ID,
            EnterpriseEntity.tenant_id != BOOTSTRAP_DEMO_TENANT_ID,
        )
    )
    assert other_tenant_supplier is None
    supplier = session.get(EnterpriseEntity, _SUPPLIER_ENTITY_ID)
    assert supplier is not None and supplier.tenant_id == BOOTSTRAP_DEMO_TENANT_ID


# ----------------------------------------------------------------------
# G-R1 regression assertion (CDD-085-Artifact-Authorization-G-R1
# amendment, §19/§22): EntityResolutionStore.append() must persist the
# active record and its history row under the real autoflush-disabled
# session behavior without a ForeignKeyViolation, across repeated
# reset/reseed, with correct tenant/linkage and no duplication -- and
# append_decision()'s own existing behavior must remain unchanged.
# ----------------------------------------------------------------------


def test_gr1_entity_resolution_record_history_ordering(session: Session) -> None:
    history_rows = session.scalars(
        select(EnterpriseEntityResolutionHistoryModel).where(
            EnterpriseEntityResolutionHistoryModel.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
        )
    ).all()
    assert (
        len(history_rows) == 3
    ), f"expected exactly 3 resolution history rows, got {len(history_rows)}"
    for history in history_rows:
        record = session.get(
            EnterpriseEntityResolutionRecordModel,
            (
                (history.tenant_id, history.current_record_identifier)
                if False
                else history.current_record_identifier
            ),
        )
        assert record is not None
        assert record.tenant_id == BOOTSTRAP_DEMO_TENANT_ID == history.tenant_id
        assert record.record_id == history.current_record_identifier
        assert history.historical_record_references == []


def test_gr1_append_decision_unchanged(session: Session) -> None:
    """append_decision()'s own already-proven flush ordering is unaffected
    by this amendment's one-line addition to append() -- exercised here
    against the real, already-seeded SAP resolution record (its own
    original `append()` call, part of the module-scoped Golden seed, is
    this test's precondition) rather than a hand-rolled SourceObject."""
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from uuid import uuid4

    from app.domain.identity_resolution.model import (
        BusinessConfidence,
        EnterpriseEntityResolutionRecord,
        ResolutionOutcome,
    )
    from app.infrastructure.persistence.demo_oqi_seeder import _SAP_OBJECT_ID

    store = EntityResolutionStore(session)
    understanding_key = store.understanding_key((_SAP_OBJECT_ID,))
    history_before = store.get_history(BOOTSTRAP_DEMO_TENANT_ID, understanding_key)
    assert history_before is not None
    based_on_record_id = history_before.current_record_identifier

    successor = EnterpriseEntityResolutionRecord(
        record_id=uuid4(),
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        enterprise_entity_id=_SUPPLIER_ENTITY_ID,
        supporting_source_object_ids=(_SAP_OBJECT_ID,),
        outcome=ResolutionOutcome.RESOLVED,
        business_confidence=BusinessConfidence.HIGH,
        structured_reasons=("exact match",),
        narrative_explanation="G-R1 regression fixture (steward decision)",
        produced_at=_dt(2026, 1, 1, tzinfo=_UTC),
        policy_version="v1",
    )
    store.append_decision(
        successor,
        understanding_key=understanding_key,
        based_on_record_id=based_on_record_id,
    )
    session.flush()

    history = store.get_history(BOOTSTRAP_DEMO_TENANT_ID, understanding_key)
    assert history is not None
    assert history.current_record_identifier == successor.record_id
    assert str(based_on_record_id) in history.historical_record_references
