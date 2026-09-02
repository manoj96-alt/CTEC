"""CDD-045 Artifact Authorization §2 row 8 -- OQI7-I1 real-PostgreSQL
integration proof. Full contract composition against real, persisted
OQI1-6/OQI5-I2 state -- never a constructed response DTO standing in for a
real evaluator/agent result -- plus tenant-isolation adversarial tests and
a static no-trust-score/no-monetary/no-Gate-F sweep. Reuses this
repository's own established sibling-test-file helper-import precedent
(`_seed_oqi1_finding`/`_seed_oqi2_finding`/`_seed_oqi3_finding` from
`test_oqi_remediation_i1.py`; `_seed_oqi1_finding_with_evaluation` and the
OQI4/OQI6 service helpers from `test_oqi_business_impact.py`)."""

# isort: skip_file
from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.application.oqi_product_experience_service import OqiProductExperienceService
from app.application.oqi_remediation_agent_service import OqiRemediationAgentService
from app.application.oqi_remediation_service import OqiRemediationError
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi_remediation.case import FindingFamily as RemediationFindingFamily
from app.infrastructure.model_provider.provider import (
    FakeModelProvider,
    ModelInvocationRequest,
    ModelInvocationResult,
)
from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
    OqiCrossSourceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_agent_repository import (
    OqiRemediationAgentPacketReader,
    OqiRemediationAgentRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import OqiRemediationRepositoryImpl
from app.tests.test_oqi_business_impact import (
    _seed_oqi1_finding_with_evaluation,
)
from app.tests.test_oqi_remediation_i1 import (
    _load_rule_and_correspondence,
    _participant_target,
    _seed_authorization,
    _seed_oqi2_finding,
    _service,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


@pytest.fixture
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(migrated_engine, expire_on_commit=False)


def _api_service(session: Session) -> OqiProductExperienceService:
    return OqiProductExperienceService(session)


# =====================================================================
# Migration/table-count invariant (CDD-045 §24, Artifact Authorization §6).
# =====================================================================


def test_oqi7_i1_introduces_zero_new_tables(migrated_engine: Engine) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(migrated_engine.url))
    alembic.command.downgrade(alembic_cfg, "0026_oqi6_reliance")
    tables = set(inspect(migrated_engine).get_table_names()) - {"alembic_version"}
    assert len(tables) == 100
    alembic.command.upgrade(alembic_cfg, "head")


# =====================================================================
# Command Center (CDD-045 §7, crown 1).
# =====================================================================


def test_command_center_counts_real_reliance_states(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        # RELIANCE_UNKNOWN: nothing evaluated yet.
        _finding_id, _ = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        row = _api_service(session).get_command_center(tenant_id=tenant_id)
    # Zero Reliance evaluations exist yet -- all counts are zero, never a
    # fabricated "supported" default (CDD-045 §17/§19).
    assert row.reliance_supported_count == 0
    assert row.reliance_at_risk_count == 0
    assert row.reliance_unknown_count == 0
    assert row.open_findings_count == 1


def test_command_center_has_no_score_field_at_dataclass_level(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        row = _api_service(session).get_command_center(tenant_id=tenant_id)
    for field_name in row.__dataclass_fields__:
        assert "score" not in field_name
        assert "monetary" not in field_name
        assert "revenue" not in field_name


# =====================================================================
# Crown: remediation != resolution; fresh evidence + real evaluator
# changes downstream product state (CDD-045 §20, §29, crowns 9/10).
# =====================================================================


def test_crown_external_remediation_does_not_resolve_finding_in_api(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _instruction_id, authorization_id = _seed_authorization(
            session, tenant_id=tenant_id
        )
        session.commit()
    with factory() as session:
        _service(session).approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="approver"
        )
        session.commit()
    with factory() as session:
        _service(session).report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()

    with factory() as session:
        detail = _api_service(session).get_finding_detail(
            tenant_id=tenant_id, finding_id=finding_id
        )
        remediation = _api_service(session).get_remediation(
            tenant_id=tenant_id, finding_id=finding_id
        )
    assert detail is not None
    assert detail.status == "OPEN"
    assert remediation is not None
    assert remediation.external_execution is not None
    assert remediation.case_status == "EXTERNAL_EXECUTION_REPORTED"


def test_crown_fresh_evidence_and_real_evaluator_resolves_finding_in_api(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _instruction_id, authorization_id = _seed_authorization(
            session, tenant_id=tenant_id
        )
        session.commit()
    with factory() as session:
        _service(session).approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="approver"
        )
        session.commit()
    with factory() as session:
        _service(session).report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()

    with factory() as session:
        rule, correspondence = _load_rule_and_correspondence(
            session, tenant_id=tenant_id, finding_id=finding_id
        )
        sap_field_id, sap_reference = _participant_target(
            rule=rule, correspondence=correspondence, role="SAP"
        )
        from app.tests.test_oqi_remediation_i1 import _admit_field_value_evidence

        _admit_field_value_evidence(
            session,
            source_field_id=sap_field_id,
            value="NEW",
            reference=sap_reference,
            observed_at=LATER,
            received_at=LATER,
        )
        session.commit()

    with factory() as session:
        rule, correspondence = _load_rule_and_correspondence(
            session, tenant_id=tenant_id, finding_id=finding_id
        )
        evaluator = OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session),
            clock=lambda: LATER + timedelta(hours=1),
        )
        evaluation = evaluator.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.commit()
    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED

    with factory() as session:
        detail = _api_service(session).get_finding_detail(
            tenant_id=tenant_id, finding_id=finding_id
        )
    assert detail is not None
    assert detail.status == "RESOLVED"


# =====================================================================
# Hostile content -- data remains data (CDD-045 §29, phase §36, closes
# disclosed gap #3). The backend obligation is exactly "data remains
# data": content survives as ordinary string values with zero
# "trusted HTML" marking and zero transformation into executable markup.
# Frontend escaping is a separate, later OQI7-I2/VM concern.
# =====================================================================

_HOSTILE_SOURCE_VALUE = "<script>alert('x')</script>"
_HOSTILE_RATIONALE = "<img src=x onerror=alert(1)> <b>ABC123</b> javascript:alert(1)"


def test_hostile_content_crown_survives_as_ordinary_data(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={"SAP": _HOSTILE_SOURCE_VALUE, "PLM": "ABC123", "MES": "ABC123", "PIM": None},
            conflicting_roles={"SAP"},
            missing_roles={"PIM"},
            authoritative_role=None,
        )
        session.commit()

    with factory() as session:
        bundle = _api_service(session).get_evidence(tenant_id=tenant_id, finding_id=finding_id)
    assert bundle is not None
    sap = next(p for p in bundle.participants if p.source_system == "SAP")
    # Exact preservation -- data remains data, no escaping/mutation, and
    # the value is a plain Python str, never wrapped in a "safe"/"trusted"
    # markup type.
    assert sap.observed_value == _HOSTILE_SOURCE_VALUE
    assert type(sap.observed_value) is str

    with factory() as session:
        remediation = _service(session)
        case, candidates = remediation.extract_candidates(
            tenant_id=tenant_id,
            finding_family=RemediationFindingFamily.OQI2,
            finding_id=finding_id,
        )
        session.commit()
    candidate_id = candidates[0].candidate_id

    def _hostile_script(request: ModelInvocationRequest) -> ModelInvocationResult:
        return ModelInvocationResult(
            succeeded=True,
            provider="fake",
            model="fake-model-v1",
            raw_text=json.dumps(
                {
                    "recommendation_type": "RECOMMEND_CANDIDATE",
                    "candidate_id": str(candidate_id),
                    "supporting_evidence_ids": [],
                    "conflicting_evidence_ids": [],
                    "impact_evaluation_ids": [],
                    "rationale": _HOSTILE_RATIONALE,
                }
            ),
            failure_kind=None,
            failure_detail="",
        )

    with factory() as session:
        agent_service = OqiRemediationAgentService(
            agent_repository=OqiRemediationAgentRepositoryImpl(session),
            packet_reader=OqiRemediationAgentPacketReader(session),
            remediation_repository=OqiRemediationRepositoryImpl(session),
            provider=FakeModelProvider(responses=_hostile_script),
        )
        outcome = agent_service.reason_about_case(
            tenant_id=tenant_id, case_id=case.case_id, now=NOW
        )
        session.commit()
    assert outcome.recommendation is not None

    with factory() as session:
        row = _api_service(session).get_agent_investigation(
            tenant_id=tenant_id, finding_id=finding_id
        )
    assert row is not None
    assert row.recommendation is not None
    assert row.recommendation.rationale == _HOSTILE_RATIONALE
    assert type(row.recommendation.rationale) is str

    # No "trusted"/"safe" rendering authority is ever introduced anywhere
    # in the OQI7-I1 response schema surface.
    import app.api.oqi.schemas as oqi_schemas

    for name in dir(oqi_schemas):
        lowered = name.lower()
        assert "html_safe" not in lowered
        assert "trusted_html" not in lowered
        assert "raw_html" not in lowered
        assert "dangerously" not in lowered


# =====================================================================
# Tenant isolation (CDD-045 §22, §29, crown 11).
# =====================================================================


def test_tenant_isolation_finding_detail(factory: sessionmaker[Session]) -> None:
    tenant_a = f"tenant-{uuid4()}"
    tenant_b = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_a)
        session.commit()

    with factory() as session:
        row = _api_service(session).get_finding_detail(tenant_id=tenant_b, finding_id=finding_id)
    assert row is None


def test_tenant_isolation_evidence(factory: sessionmaker[Session]) -> None:
    tenant_a = f"tenant-{uuid4()}"
    tenant_b = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_a,
            roles={"SAP": "ABC123", "PLM": "ABC123"},
            conflicting_roles=set(),
            missing_roles=set(),
            authoritative_role=None,
        )
        session.commit()

    with factory() as session:
        bundle = _api_service(session).get_evidence(tenant_id=tenant_b, finding_id=finding_id)
    assert bundle is None


def test_tenant_isolation_decide_authorization_fails_closed(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        _, _, authorization_id = _seed_authorization(session, tenant_id=tenant_a)
        session.commit()

    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _api_service(session).decide_authorization(
                tenant_id=f"tenant-{uuid4()}",
                authorization_id=authorization_id,
                approve=True,
                decided_by="approver",
                rejection_reason=None,
            )
        assert excinfo.value.code == "REMEDIATION_TENANT_MISMATCH"


def test_get_remediation_exposes_real_authorization_id_and_it_operates_decide(
    factory: sessionmaker[Session],
) -> None:
    """OQI-UX authorization-ID contract correction: proves the API contract
    is operationally complete end-to-end -- GET remediation returns the
    real, persisted authorization_id, that exact ID successfully drives the
    real decide route for its own tenant, and the same exact ID still fails
    closed for a different tenant. Knowledge of the ID is resource identity,
    never authority (CDD-045 companion, authorization_id != authority)."""
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _instruction_id, real_authorization_id = _seed_authorization(
            session, tenant_id=tenant_a
        )
        session.commit()

    with factory() as session:
        remediation = _api_service(session).get_remediation(
            tenant_id=tenant_a, finding_id=finding_id
        )
    assert remediation is not None
    assert remediation.authorization is not None
    assert remediation.authorization.authorization_id == real_authorization_id

    with factory() as session:
        case_status = _api_service(session).decide_authorization(
            tenant_id=tenant_a,
            authorization_id=remediation.authorization.authorization_id,
            approve=True,
            decided_by="approver",
            rejection_reason=None,
        )
        session.commit()
    assert case_status == "APPROVED"

    with factory() as session:
        _finding_id_b, _instruction_id_b, other_real_authorization_id = _seed_authorization(
            session, tenant_id=f"tenant-{uuid4()}"
        )
        session.commit()
    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _api_service(session).decide_authorization(
                tenant_id=tenant_a,
                authorization_id=other_real_authorization_id,
                approve=True,
                decided_by="approver",
                rejection_reason=None,
            )
        assert excinfo.value.code == "REMEDIATION_TENANT_MISMATCH"


def test_tenant_isolation_command_center_counts_are_isolated(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    tenant_b = f"tenant-{uuid4()}"
    with factory() as session:
        _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_a)
        session.commit()

    with factory() as session:
        row_b = _api_service(session).get_command_center(tenant_id=tenant_b)
    assert row_b.open_findings_count == 0


# =====================================================================
# Pagination.
# =====================================================================


def test_pagination_returns_stable_pages(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        for _ in range(5):
            _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        page1, cursor1 = _api_service(session).list_findings(
            tenant_id=tenant_id, family=None, status=None, limit=2, cursor=None
        )
    assert len(page1) == 2
    assert cursor1 is not None

    with factory() as session:
        page2, _cursor2 = _api_service(session).list_findings(
            tenant_id=tenant_id, family=None, status=None, limit=2, cursor=cursor1
        )
    assert len(page2) == 2
    ids1 = {row.finding.finding_id for row in page1}
    ids2 = {row.finding.finding_id for row in page2}
    assert ids1.isdisjoint(ids2)


# =====================================================================
# Static sweep: no trust score / monetary field / Gate F import anywhere
# in the OQI7-I1 surface (CDD-045 §8, §26).
# =====================================================================

_OQI7_I1_FILES = (
    "app/api/oqi/router.py",
    "app/api/oqi/schemas.py",
    "app/api/oqi/dependencies.py",
    "app/application/oqi_product_experience_service.py",
)

_PROHIBITED_IDENTIFIER_SUBSTRINGS = (
    "trust_score",
    "reliability_score",
    "confidence_score",
    "business_impact_score",
    "criticality_score",
    "quality_health_score",
    "revenue_exposure",
    "monetary_impact",
    "dollar_impact",
    "cost_impact",
)


def test_no_trust_score_or_monetary_identifier_anywhere_in_oqi7_i1() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    for relative_path in _OQI7_I1_FILES:
        source = (repo_root / "backend" / relative_path).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, (ast.Attribute,)):
                name = node.attr
            elif isinstance(node, ast.FunctionDef):
                name = node.name
            if name is None:
                continue
            lowered = name.lower()
            for prohibited in _PROHIBITED_IDENTIFIER_SUBSTRINGS:
                assert prohibited not in lowered, f"{relative_path}: {name!r}"


def test_no_gate_f_import_anywhere_in_oqi7_i1() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    for relative_path in _OQI7_I1_FILES:
        source = (repo_root / "backend" / relative_path).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert "gate_f" not in node.module
                assert "supply_chain_impact" not in node.module
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "gate_f" not in alias.name
                    assert "supply_chain_impact" not in alias.name


def test_no_direct_finding_status_mutation_in_oqi7_i1() -> None:
    """OQI7-I1 reads only -- the two action endpoints call OQI5-I1's
    existing service methods, never assigning `.status =` directly on any
    Finding ORM (CDD-045 §55)."""
    repo_root = Path(__file__).resolve().parents[3]
    for relative_path in _OQI7_I1_FILES:
        source = (repo_root / "backend" / relative_path).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "status":
                        pytest.fail(f"{relative_path}: direct '.status =' assignment found")


def test_no_model_provider_import_in_oqi7_i1() -> None:
    """CDD-045 §109-110: product reads never trigger agent reasoning --
    zero model-provider dependency anywhere in the read/action surface."""
    repo_root = Path(__file__).resolve().parents[3]
    for relative_path in _OQI7_I1_FILES:
        source = (repo_root / "backend" / relative_path).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert "model_provider" not in node.module
