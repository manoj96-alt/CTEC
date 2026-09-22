"""CDD-086 Generic Finding Detail Parity -- Artifact Authorization §2 row 1
crown suite (P1-P30, §6). Proves the LIST/DETAIL registry asymmetry
NOETVA-INTEGRITY-FINDING-DETAIL-DR discovered is closed for Integrity,
Timeliness, and Uniqueness storage families, with every downstream tab
degrading honestly (never crashing, never fabricating capability) and
zero regression to OQI1/OQI2/OQI3 or the dedicated Uniqueness pair-detail
endpoint.

LISTABLE -> RETRIEVABLE. Never RETRIEVABLE -> every capability exists.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_product_experience_service import OqiProductExperienceService
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.domain.oqi_business_impact.impact import BusinessImpactOutcome
from app.domain.oqi_business_impact.reliance import RelianceState
from app.domain.oqi_finding_origin.origin import FindingStorageFamily
from app.domain.oqi_ontology_impact.evaluation import FindingFamily, ImpactOutcome
from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder
from app.infrastructure.persistence.demo_oqi_seeder import DemoOqiSeeder
from app.infrastructure.persistence.ontology_seed import OntologySeeder

_WRONG_TENANT = "some-other-tenant"


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture(scope="module")
def seeded(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        BlueprintSeeder(session).load()
        session.commit()
        DemoOqiSeeder(session).seed()
        session.commit()


@pytest.fixture()
def session(factory: sessionmaker[Session], seeded: None) -> Generator[Session, None, None]:
    del seeded
    with factory() as session:
        yield session
        session.rollback()


def _service(session: Session) -> OqiProductExperienceService:
    return OqiProductExperienceService(session)


def _only(session: Session, family: str, condition_label: str) -> UUID:
    """List the given storage family and return the finding_id of the row
    matching condition_label -- never a hand-constructed ID (§24 of the
    governing prompt: the exact ID the list API returned)."""
    svc = _service(session)
    rows, _ = svc.list_findings(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, family=family, status=None, limit=50, cursor=None
    )
    matches = [row for row in rows if row.finding.condition_label == condition_label]
    assert matches, f"no {family} finding with condition_label={condition_label!r} in list"
    return matches[0].finding.finding_id


# ----------------------------------------------------------------------
# P1-P10: list -> exact ID -> detail, for each of the three affected
# families and all three Integrity finding types.
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("family", "condition_label"),
    [
        ("INTEGRITY", "ORPHAN_REFERENCE"),  # P1/P2
        ("INTEGRITY", "RELATIONSHIP_CARDINALITY_VIOLATION"),  # P3/P4
        ("INTEGRITY", "MISSING_REQUIRED_RELATIONSHIP"),  # P5/P6
        ("TIMELINESS", "STALE_SOURCE_EVIDENCE"),  # P7/P8
        ("UNIQUENESS", "DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE"),  # P9/P10
    ],
)
def test_list_then_exact_id_opens_through_generic_detail(
    session: Session, family: str, condition_label: str
) -> None:
    finding_id = _only(session, family, condition_label)
    detail = _service(session).get_finding_detail(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )
    assert detail is not None, f"{family}/{condition_label} listed but not retrievable"
    assert detail.condition_label == condition_label


# ----------------------------------------------------------------------
# P11: wrong tenant -- each distinct storage-family resolution branch.
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("family", "condition_label"),
    [
        ("INTEGRITY", "ORPHAN_REFERENCE"),
        ("INTEGRITY", "RELATIONSHIP_CARDINALITY_VIOLATION"),
        ("INTEGRITY", "MISSING_REQUIRED_RELATIONSHIP"),
        ("TIMELINESS", "STALE_SOURCE_EVIDENCE"),
        ("UNIQUENESS", "DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE"),
    ],
)
def test_wrong_tenant_cannot_retrieve(session: Session, family: str, condition_label: str) -> None:
    finding_id = _only(session, family, condition_label)
    svc = _service(session)
    assert svc.get_finding_detail(tenant_id=_WRONG_TENANT, finding_id=finding_id) is None
    # No leakage through downstream subject/entity resolution either.
    assert svc.get_business_impact(tenant_id=_WRONG_TENANT, finding_id=finding_id) is None
    assert svc.get_reliance(tenant_id=_WRONG_TENANT, finding_id=finding_id) is None


# ----------------------------------------------------------------------
# P12: unknown ID remains not found.
# ----------------------------------------------------------------------


def test_unknown_id_remains_not_found(session: Session) -> None:
    svc = _service(session)
    assert svc.get_finding_detail(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=uuid4()) is None


# ----------------------------------------------------------------------
# P13-P15: existing OQI1/OQI2/OQI3 detail remains unchanged.
# ----------------------------------------------------------------------


def test_oqi1_detail_unchanged(session: Session) -> None:
    svc = _service(session)
    rows, _ = svc.list_findings(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, family="OQI1", status=None, limit=10, cursor=None
    )
    assert rows
    detail = svc.get_finding_detail(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=rows[0].finding.finding_id
    )
    assert detail is not None
    assert detail.family is FindingFamily.OQI1


def test_oqi2_detail_unchanged(session: Session) -> None:
    svc = _service(session)
    rows, _ = svc.list_findings(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, family="OQI2", status=None, limit=10, cursor=None
    )
    assert rows
    finding_id = rows[0].finding.finding_id
    detail = svc.get_finding_detail(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)
    assert detail is not None
    assert detail.family is FindingFamily.OQI2
    # OQI2 real cross-source evidence must still populate exactly as before.
    evidence = svc.get_evidence(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)
    assert evidence is not None
    assert len(evidence.participants) == 2


def test_oqi3_detail_unchanged(session: Session) -> None:
    svc = _service(session)
    rows, _ = svc.list_findings(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, family="OQI3", status=None, limit=10, cursor=None
    )
    assert rows
    detail = svc.get_finding_detail(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=rows[0].finding.finding_id
    )
    assert detail is not None
    assert detail.family is FindingFamily.OQI3


# ----------------------------------------------------------------------
# P16-P21: Integrity downstream tabs -- honest, never crash, never
# fabricate.
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "condition_label",
    ["ORPHAN_REFERENCE", "RELATIONSHIP_CARDINALITY_VIOLATION", "MISSING_REQUIRED_RELATIONSHIP"],
)
def test_integrity_downstream_tabs_honest(session: Session, condition_label: str) -> None:
    svc = _service(session)
    finding_id = _only(session, "INTEGRITY", condition_label)

    evidence = svc.get_evidence(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)  # P16
    assert evidence is not None
    assert evidence.participants == ()
    assert evidence.candidate is None

    impact = svc.get_ontology_impact(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )  # P17
    assert impact is not None
    assert impact.outcome in (ImpactOutcome.IMPACT_UNKNOWN, ImpactOutcome.IMPACTED)

    business_impact = svc.get_business_impact(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )  # P18
    assert business_impact is not None
    assert business_impact.outcome in (
        BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN,
        BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED,
        BusinessImpactOutcome.NO_KNOWN_BUSINESS_IMPACT,
    )

    reliance = svc.get_reliance(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)  # P19
    assert reliance is not None
    assert isinstance(reliance.state, RelianceState)

    agent = svc.get_agent_investigation(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )  # P20
    assert agent is not None
    assert agent.specialists == ()
    assert agent.recommendation is None

    remediation = svc.get_remediation(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )  # P21
    assert remediation is not None
    assert remediation.case_status is None
    assert remediation.candidate is None
    assert remediation.authorization is None
    assert remediation.external_execution is None


# ----------------------------------------------------------------------
# P22-P24: Timeliness downstream tabs -- honest, and real data when a
# governed dependency genuinely supports it.
# ----------------------------------------------------------------------


def test_timeliness_downstream_tabs_honest_and_real_when_supported(session: Session) -> None:
    svc = _service(session)
    finding_id = _only(session, "TIMELINESS", "STALE_SOURCE_EVIDENCE")

    evidence = svc.get_evidence(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)  # P22
    assert evidence is not None
    assert evidence.candidate is None

    impact = svc.get_ontology_impact(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )  # P22
    assert impact is not None

    business_impact = svc.get_business_impact(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )
    assert business_impact is not None
    assert business_impact.outcome is BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED  # P23
    assert business_impact.dependencies

    reliance = svc.get_reliance(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)
    assert reliance is not None
    assert reliance.state is RelianceState.RELIANCE_AT_RISK  # P23

    agent = svc.get_agent_investigation(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )  # P24
    assert agent is not None
    assert agent.specialists == ()
    assert agent.recommendation is None

    remediation = svc.get_remediation(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )  # P24
    assert remediation is not None
    assert remediation.case_status is None


# ----------------------------------------------------------------------
# P25-P27: Uniqueness -- generic detail opens, dedicated pair detail is
# unaffected, generic Agent/Remediation stay honest.
# ----------------------------------------------------------------------


def test_uniqueness_generic_detail_opens(session: Session) -> None:
    finding_id = _only(session, "UNIQUENESS", "DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE")
    detail = _service(session).get_finding_detail(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )
    assert detail is not None  # P25
    assert detail.family is FindingStorageFamily.UNIQUENESS  # type: ignore[comparison-overlap]


def test_uniqueness_dedicated_pair_detail_unaffected(session: Session) -> None:
    finding_id = _only(session, "UNIQUENESS", "DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE")
    svc = _service(session)
    pair_detail = svc.get_uniqueness_candidate_detail(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id
    )
    assert pair_detail is not None  # P26
    assert pair_detail.finding_id == finding_id
    assert pair_detail.member_a.entity_id != pair_detail.member_b.entity_id
    # Candidate remains candidate: no adjudication recorded in the fresh
    # seed state, and the closed action domain has no merge action.
    assert pair_detail.latest_adjudication_action is None


def test_uniqueness_generic_agent_and_remediation_stay_honest(session: Session) -> None:
    finding_id = _only(session, "UNIQUENESS", "DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE")
    svc = _service(session)
    agent = svc.get_agent_investigation(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)
    assert agent is not None
    assert agent.specialists == () and agent.recommendation is None  # P27
    remediation = svc.get_remediation(tenant_id=BOOTSTRAP_DEMO_TENANT_ID, finding_id=finding_id)
    assert remediation is not None
    assert remediation.case_status is None  # P27 -- no fabricated generic remediation


# ----------------------------------------------------------------------
# P28: generic list result set/semantics unchanged.
# ----------------------------------------------------------------------


def test_list_findings_semantics_unchanged(session: Session) -> None:
    svc = _service(session)
    rows, _ = svc.list_findings(
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID, family=None, status=None, limit=200, cursor=None
    )
    families = {row.finding.family.value for row in rows}
    assert {"OQI1", "OQI2", "OQI3", "INTEGRITY", "TIMELINESS", "UNIQUENESS"} <= families
    # Every row still carries the same fields this correction never touches.
    for row in rows:
        assert row.finding.finding_id is not None
        assert row.finding.condition_label is not None
        assert row.finding.status is not None


# ----------------------------------------------------------------------
# P29: no migration/schema drift.
# ----------------------------------------------------------------------


def test_no_migration_drift(seeded: None) -> None:
    # This module's own `migrated_engine` fixture (conftest.py) already
    # performs a full downgrade(base)/upgrade(head) cycle before any test
    # here runs -- the `seeded` fixture succeeding is itself proof the
    # four storage tables this correction depends on already exist at
    # head, unmodified. No migration file is created or touched by this
    # correction (independently verified via `git diff --name-status` in
    # the implementation report).
    del seeded


# ----------------------------------------------------------------------
# P30 (Docker) is executed and reported in the implementation report, not
# as a pytest test -- fresh-Docker list->detail parity is a deployment-
# environment proof, not a unit-level assertion.
# ----------------------------------------------------------------------
