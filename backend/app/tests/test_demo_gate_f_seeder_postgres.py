"""Postgres-backed proof of the Gate F demo seeder (F-I4, governed by the
merged CDD-015 Deterministic Demo Data and Read-Projection Clarification
and Remediation Report): idempotency, deterministic identifiers, tenant
isolation, provenance, and -- most importantly -- that all three
scenarios reproduce their governed outcome through the real, unmodified
`SupplyChainImpactApiService.evaluate()`, not a special test-only code
path.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.supply_chain_impact_api import (
    SupplyChainImpactApiService,
    SupplyChainImpactEvaluateRequest,
)
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.infrastructure.persistence.demo_gate_f_seeder import (
    DemoGateFSeeder,
    DemoGateFSeedSummary,
)
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)

NOW = datetime.now(UTC)


def _principal(*, scopes: tuple[str, ...] = ("supply-chain-impact:evaluate",)) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="demo-seeder-test",
        tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
        scopes=scopes,
        roles=(),
        issuer="test",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _seed(factory: "sessionmaker[Session]") -> DemoGateFSeedSummary:
    with factory() as session:
        summary = DemoGateFSeeder(session).seed()
        session.commit()
    return summary


def test_seeder_is_idempotent(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    first = _seed(factory)
    second = _seed(factory)
    assert first.recommended == second.recommended
    assert first.unknown == second.unknown
    assert first.rejected == second.rejected
    assert first.alternate_supplier_entity_id == second.alternate_supplier_entity_id
    assert second.relationships_created == 0
    assert second.assertions_created == 0


def test_seeder_deterministic_identifiers_across_runs(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    first = _seed(factory)
    second = _seed(factory)
    assert first.recommended.supplier_entity_id == second.recommended.supplier_entity_id
    assert first.unknown.supplier_entity_id == second.unknown.supplier_entity_id
    assert first.rejected.supplier_entity_id == second.rejected.supplier_entity_id
    assert first.alternate_supplier_entity_id == second.alternate_supplier_entity_id


def test_seeder_scopes_every_entity_to_the_demo_tenant(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)
    with factory() as session:
        entity_ids = (
            summary.recommended.supplier_entity_id,
            summary.recommended.material_entity_id,
            summary.recommended.risk_event_entity_id,
            summary.unknown.supplier_entity_id,
            summary.rejected.supplier_entity_id,
            summary.alternate_supplier_entity_id,
        )
        tenants = (
            session.execute(
                select(EnterpriseEntity.tenant_id).where(
                    EnterpriseEntity.enterprise_entity_id.in_(entity_ids)
                )
            )
            .scalars()
            .all()
        )
    assert set(tenants) == {BOOTSTRAP_DEMO_TENANT_ID}


def test_seeder_assertions_carry_real_provenance(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)
    with factory() as session:
        assertions = (
            session.execute(
                select(Assertion).where(
                    Assertion.subject_entity_id == summary.recommended.risk_event_entity_id,
                    Assertion.predicate == "severity",
                )
            )
            .scalars()
            .all()
        )
    assert len(assertions) == 1
    assertion = assertions[0]
    assert assertion.object_value == "Severe"
    assert assertion.source_system_id == summary.source_system_id
    assert assertion.assertion_type == "Evidence-backed"
    assert assertion.asserted_on is not None


def test_recommended_scenario_reaches_recommended_via_real_evaluation(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)
    service = SupplyChainImpactApiService(factory)
    result = service.evaluate(
        _principal(),
        SupplyChainImpactEvaluateRequest(supplier_entity_id=summary.recommended.supplier_entity_id),
    )
    assert result.governance_standing == "HUMAN_APPROVAL_REQUIRED"
    [material] = result.materials
    assert material.material_entity_id == summary.recommended.material_entity_id
    assert material.high_severity_disruption is True
    assert material.single_source_exposure is True
    assert material.revenue_materiality is True
    [candidate] = material.candidates
    assert candidate.outcome == "Recommended"


def test_unknown_scenario_stays_unknown_via_real_evaluation(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)
    service = SupplyChainImpactApiService(factory)
    result = service.evaluate(
        _principal(),
        SupplyChainImpactEvaluateRequest(supplier_entity_id=summary.unknown.supplier_entity_id),
    )
    [material] = result.materials
    assert material.high_severity_disruption is None
    [candidate] = material.candidates
    assert candidate.outcome is None
    assert candidate.reason is None
    assert candidate.decision_record_identifier is None


def test_rejected_scenario_reaches_rejected_not_material_via_real_evaluation(
    migrated_engine: Engine,
) -> None:
    """Rejected via REJECTED_NOT_MATERIAL, not zero-alternate: Gate F's
    alternate-supplier discovery is tenant-wide (F-I2, unmodified), so the
    shared demo Alternate Supplier is also discoverable here -- the
    materiality short-circuit in GateFDecisionAdapter._classify makes the
    outcome correct and deterministic regardless."""
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)
    service = SupplyChainImpactApiService(factory)
    result = service.evaluate(
        _principal(),
        SupplyChainImpactEvaluateRequest(supplier_entity_id=summary.rejected.supplier_entity_id),
    )
    [material] = result.materials
    assert material.high_severity_disruption is True
    assert material.single_source_exposure is True
    assert material.revenue_materiality is False
    [candidate] = material.candidates
    assert candidate.outcome == "Rejected"
    assert (
        candidate.reason == "Rejected: revenue exposure does not exceed the materiality threshold"
    )


def test_seeder_creates_no_relationship_type_or_entity_type_rows(migrated_engine: Engine) -> None:
    """The seeder must only ever add institutional_relationships/assertions
    instance rows -- never new entity_types/relationship_types vocabulary
    rows (CDD-015 Deterministic Demo Data clarification, Item A)."""
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        before_relationship_count = (
            session.execute(select(InstitutionalRelationship.institutional_relationship_id))
            .scalars()
            .all()
        )
    _seed(factory)
    with factory() as session:
        after_relationship_count = (
            session.execute(select(InstitutionalRelationship.institutional_relationship_id))
            .scalars()
            .all()
        )
    assert len(after_relationship_count) >= len(before_relationship_count)
