"""Explicit, idempotent, demo-only seeder for the Gate F Supply Chain
Impact demonstration scenarios (F-I4, governed by the merged CDD-015
Deterministic Demo Data and Read-Projection Clarification and
Remediation Report).

Never invoked by normal production bootstrap: app.main.lifespan only
ever builds the dependency Container (see app/main.py) -- nothing there,
or anywhere else on the request path, calls this module. It has its own,
separate, manually-run CLI entrypoint (see __main__ below) and must be
invoked deliberately -- following demo_ontology_copilot_seeder.py's exact
precedent.

Refuses to seed any tenant other than the labeled demo tenant
(BOOTSTRAP_DEMO_TENANT_ID). Persists three independent, deterministic Gate
F scenarios through the real, authorized mechanism -- institutional_
relationships and assertions, tenant-scoped per RFC-016 -- using only the
ten pre-existing RFC-017 SS1 concepts and the RFC-017 SS3 relationship
types Gate F F-I1 already seeded (assembledAt, coveredBy, candidateFor)
alongside the seven pre-existing ones:

    RECOMMENDED scenario:
        Supplier(R) --locatedIn--> Region(R) --exposedTo--> RiskEvent(R,
        severity=Severe)
        Supplier(R) --supplies--> Material(R) --usedIn--> BOM(R)
            --defines--> Product(R) --assembledAt--> Facility(R)
        Product(R) --generatesRevenue--> RevenueExposure(R,
        annualRevenueUsd=12,000,000)
        AlternateSupplier(shared) with qualification=true, capacity=true

    UNKNOWN scenario:
        Same shape, its own Region/RiskEvent -- but the RiskEvent carries
        NO severity assertion (evidence genuinely absent, never asserted
        false).

    REJECTED scenario:
        Same shape, its own Region/RiskEvent (severity=Severe) -- but its
        RevenueExposure carries annualRevenueUsd=5,000,000 (asserted,
        real, below the frozen $10,000,000 materiality threshold).
        Rejected via the governed REJECTED_NOT_MATERIAL path, not via
        "zero viable alternate": Gate F's alternate-supplier discovery is
        tenant-wide, not material-scoped (F-I2, unmodified) -- the single
        AlternateSupplier entity seeded for the RECOMMENDED scenario is
        therefore also discoverable as a candidate against this
        scenario's Material. REJECTED_NOT_MATERIAL short-circuits ahead
        of the no-viable-alternate check in GateFDecisionAdapter._classify
        (backend/app/integration/adapters/gate_f/drm.py), so this
        scenario's outcome is correct and deterministic regardless of
        that shared-tenant alternate-discovery behavior -- unlike a
        "zero viable alternate" design, which a shared alternate supplier
        would silently turn into RECOMMENDED instead. This is a scenario
        DESIGN choice made to fit Gate F's existing, frozen, unmodified
        business logic; it does not change or work around that logic.

Calls OntologySeeder(session).load() first (idempotent) to guarantee every
entity type and relationship type this seeder depends on already exists,
regardless of invocation order.

Idempotent: every id used is deterministic (uuid5, namespaced under the
existing BOOTSTRAP_SEED_NAMESPACE), and every write is preceded by an
existence check, so running seed() twice against the same database
creates nothing new the second time.
"""

from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    SEED_TIMESTAMP,
)
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.ontology_seed import OntologySeeder

RECOMMENDED_ANNUAL_REVENUE_USD = "12000000"
REJECTED_ANNUAL_REVENUE_USD = "5000000"

_REQUIRED_ENTITY_TYPES = (
    "Supplier",
    "Material",
    "BOM",
    "Product",
    "Facility",
    "Revenue Exposure",
    "Region",
    "Risk Event",
    "Alternate Supplier",
)
_REQUIRED_RELATIONSHIP_TYPES = (
    "supplies",
    "usedIn",
    "defines",
    "assembledAt",
    "generatesRevenue",
    "locatedIn",
    "exposedTo",
)


class DemoTenantRequiredError(Exception):
    """Raised when the seeder is asked to seed any tenant other than the
    labeled demo tenant."""


@dataclass(frozen=True, slots=True)
class DemoEntitySeedResult:
    entity_id: UUID
    created: bool


@dataclass(frozen=True, slots=True)
class DemoGateFScenarioSummary:
    supplier_entity_id: UUID
    material_entity_id: UUID
    risk_event_entity_id: UUID


@dataclass(frozen=True, slots=True)
class DemoGateFSeedSummary:
    tenant_id: str
    source_system_id: UUID
    recommended: DemoGateFScenarioSummary
    unknown: DemoGateFScenarioSummary
    rejected: DemoGateFScenarioSummary
    alternate_supplier_entity_id: UUID
    relationships_created: int
    assertions_created: int


class DemoGateFSeeder:
    """Test-covered in test_demo_gate_f_seeder.py and
    test_demo_gate_f_seeder_postgres.py."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def seed(self, tenant_id: str = BOOTSTRAP_DEMO_TENANT_ID) -> DemoGateFSeedSummary:
        if tenant_id != BOOTSTRAP_DEMO_TENANT_ID:
            raise DemoTenantRequiredError(
                f"The demo Gate F seeder refuses to seed tenant {tenant_id!r}; "
                f"it only ever seeds the labeled demo tenant {BOOTSTRAP_DEMO_TENANT_ID!r}."
            )

        OntologySeeder(self._session).load()
        self._session.flush()

        entity_type_ids = self._entity_type_ids(_REQUIRED_ENTITY_TYPES)
        relationship_type_ids = self._relationship_type_ids(_REQUIRED_RELATIONSHIP_TYPES)
        source_system_id = self._seed_source_system(tenant_id, "Gate F Demo Risk Platform")
        revenue_source_id = self._seed_source_system(tenant_id, "Gate F Demo Finance/BI")
        supplier_source_id = self._seed_source_system(tenant_id, "Gate F Demo Supplier Portal")

        relationships_created = 0
        assertions_created = 0

        alternate_supplier = self._entity(
            tenant_id,
            "gate-f-demo:alternate-supplier",
            "Demo Alternate Supplier (Gate F)",
            entity_type_ids["Alternate Supplier"],
        )
        assertions_created += self._assert_literal(
            tenant_id,
            "gate-f-demo:alternate-supplier:qualification",
            subject_entity_id=alternate_supplier.entity_id,
            predicate="qualification",
            object_value="true",
            source_system_id=supplier_source_id,
        )
        assertions_created += self._assert_literal(
            tenant_id,
            "gate-f-demo:alternate-supplier:capacity",
            subject_entity_id=alternate_supplier.entity_id,
            predicate="capacity",
            object_value="true",
            source_system_id=supplier_source_id,
        )
        assertions_created += self._assert_literal(
            tenant_id,
            "gate-f-demo:alternate-supplier:lead-time-days",
            subject_entity_id=alternate_supplier.entity_id,
            predicate="leadTimeDays",
            object_value="21",
            source_system_id=supplier_source_id,
        )
        assertions_created += self._assert_literal(
            tenant_id,
            "gate-f-demo:alternate-supplier:cost-usd",
            subject_entity_id=alternate_supplier.entity_id,
            predicate="costUsd",
            object_value="185000",
            source_system_id=supplier_source_id,
        )

        recommended, created, asserted = self._seed_scenario(
            tenant_id,
            label="recommended",
            entity_type_ids=entity_type_ids,
            relationship_type_ids=relationship_type_ids,
            severity="Severe",
            annual_revenue_usd=RECOMMENDED_ANNUAL_REVENUE_USD,
            source_system_id=source_system_id,
            revenue_source_id=revenue_source_id,
        )
        relationships_created += created
        assertions_created += asserted

        unknown, created, asserted = self._seed_scenario(
            tenant_id,
            label="unknown",
            entity_type_ids=entity_type_ids,
            relationship_type_ids=relationship_type_ids,
            severity=None,
            annual_revenue_usd=RECOMMENDED_ANNUAL_REVENUE_USD,
            source_system_id=source_system_id,
            revenue_source_id=revenue_source_id,
        )
        relationships_created += created
        assertions_created += asserted

        rejected, created, asserted = self._seed_scenario(
            tenant_id,
            label="rejected",
            entity_type_ids=entity_type_ids,
            relationship_type_ids=relationship_type_ids,
            severity="Severe",
            annual_revenue_usd=REJECTED_ANNUAL_REVENUE_USD,
            source_system_id=source_system_id,
            revenue_source_id=revenue_source_id,
        )
        relationships_created += created
        assertions_created += asserted

        return DemoGateFSeedSummary(
            tenant_id=tenant_id,
            source_system_id=source_system_id,
            recommended=recommended,
            unknown=unknown,
            rejected=rejected,
            alternate_supplier_entity_id=alternate_supplier.entity_id,
            relationships_created=relationships_created,
            assertions_created=assertions_created,
        )

    def _seed_scenario(
        self,
        tenant_id: str,
        *,
        label: str,
        entity_type_ids: dict[str, UUID],
        relationship_type_ids: dict[str, UUID],
        severity: str | None,
        annual_revenue_usd: str,
        source_system_id: UUID,
        revenue_source_id: UUID,
    ) -> tuple[DemoGateFScenarioSummary, int, int]:
        def label_id(suffix: str) -> str:
            return f"gate-f-demo:{label}:{suffix}"

        supplier = self._entity(
            tenant_id, label_id("supplier"), f"Demo Supplier ({label})", entity_type_ids["Supplier"]
        )
        region = self._entity(
            tenant_id, label_id("region"), f"Demo Region ({label})", entity_type_ids["Region"]
        )
        risk_event = self._entity(
            tenant_id,
            label_id("risk-event"),
            f"Demo Risk Event ({label})",
            entity_type_ids["Risk Event"],
        )
        material = self._entity(
            tenant_id, label_id("material"), f"Demo Material ({label})", entity_type_ids["Material"]
        )
        bom = self._entity(
            tenant_id, label_id("bom"), f"Demo BOM ({label})", entity_type_ids["BOM"]
        )
        product = self._entity(
            tenant_id, label_id("product"), f"Demo Product ({label})", entity_type_ids["Product"]
        )
        facility = self._entity(
            tenant_id, label_id("facility"), f"Demo Facility ({label})", entity_type_ids["Facility"]
        )
        revenue_exposure = self._entity(
            tenant_id,
            label_id("revenue-exposure"),
            f"Demo Revenue Exposure ({label})",
            entity_type_ids["Revenue Exposure"],
        )

        relationships_created = 0
        for suffix, relationship_type_name, from_id, to_id in (
            ("locatedIn", "locatedIn", supplier.entity_id, region.entity_id),
            ("exposedTo", "exposedTo", region.entity_id, risk_event.entity_id),
            ("supplies", "supplies", supplier.entity_id, material.entity_id),
            ("usedIn", "usedIn", material.entity_id, bom.entity_id),
            ("defines", "defines", bom.entity_id, product.entity_id),
            ("assembledAt", "assembledAt", product.entity_id, facility.entity_id),
            (
                "generatesRevenue",
                "generatesRevenue",
                product.entity_id,
                revenue_exposure.entity_id,
            ),
        ):
            if self._relate(
                tenant_id,
                label_id(suffix),
                f"Demo: {suffix} ({label})",
                relationship_type_ids[relationship_type_name],
                from_id,
                to_id,
            ):
                relationships_created += 1

        assertions_created = 0
        if severity is not None:
            assertions_created += self._assert_literal(
                tenant_id,
                label_id("risk-event:severity"),
                subject_entity_id=risk_event.entity_id,
                predicate="severity",
                object_value=severity,
                source_system_id=source_system_id,
            )
        assertions_created += self._assert_literal(
            tenant_id,
            label_id("revenue-exposure:annual-revenue-usd"),
            subject_entity_id=revenue_exposure.entity_id,
            predicate="annualRevenueUsd",
            object_value=annual_revenue_usd,
            source_system_id=revenue_source_id,
        )

        summary = DemoGateFScenarioSummary(
            supplier_entity_id=supplier.entity_id,
            material_entity_id=material.entity_id,
            risk_event_entity_id=risk_event.entity_id,
        )
        return summary, relationships_created, assertions_created

    def _entity_type_ids(self, names: tuple[str, ...]) -> dict[str, UUID]:
        rows = self._session.execute(
            select(EntityType.entity_type_name, EntityType.entity_type_id).where(
                EntityType.entity_type_name.in_(names)
            )
        ).all()
        found = {name: entity_type_id for name, entity_type_id in rows}
        missing = set(names) - set(found)
        if missing:
            raise RuntimeError(
                f"Demo Gate F seeder: required entity type(s) not found after "
                f"OntologySeeder.load(): {sorted(missing)}"
            )
        return found

    def _relationship_type_ids(self, names: tuple[str, ...]) -> dict[str, UUID]:
        rows = self._session.execute(
            select(
                RelationshipType.relationship_type_name, RelationshipType.relationship_type_id
            ).where(RelationshipType.relationship_type_name.in_(names))
        ).all()
        found = {name: relationship_type_id for name, relationship_type_id in rows}
        missing = set(names) - set(found)
        if missing:
            raise RuntimeError(
                f"Demo Gate F seeder: required relationship type(s) not found after "
                f"OntologySeeder.load(): {sorted(missing)}"
            )
        return found

    def _demo_id(self, label: str) -> UUID:
        return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"gate-f-demo:{label}")

    def _entity(
        self, tenant_id: str, label: str, name: str, entity_type_id: UUID
    ) -> DemoEntitySeedResult:
        entity_id = self._demo_id(label)
        if self._session.get(EnterpriseEntity, entity_id) is not None:
            return DemoEntitySeedResult(entity_id=entity_id, created=False)
        self._session.add(
            EnterpriseEntity(
                enterprise_entity_id=entity_id,
                tenant_id=tenant_id,
                enterprise_entity_name=name,
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                entity_type_id=entity_type_id,
                business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
            )
        )
        self._session.flush()
        return DemoEntitySeedResult(entity_id=entity_id, created=True)

    def _relate(
        self,
        tenant_id: str,
        label: str,
        name: str,
        relationship_type_id: UUID,
        from_entity_id: UUID,
        to_entity_id: UUID,
    ) -> bool:
        relationship_id = self._demo_id(f"relationship:{label}")
        if self._session.get(InstitutionalRelationship, relationship_id) is not None:
            return False
        self._session.add(
            InstitutionalRelationship(
                institutional_relationship_id=relationship_id,
                tenant_id=tenant_id,
                institutional_relationship_name=name,
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                relationship_type_id=relationship_type_id,
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
            )
        )
        self._session.flush()
        return True

    def _seed_source_system(self, tenant_id: str, name: str) -> UUID:
        identifier = self._demo_id(f"source-system:{name}")
        if self._session.get(SourceSystem, identifier) is None:
            self._session.add(
                SourceSystem(
                    source_system_id=identifier,
                    tenant_id=tenant_id,
                    source_system_name=name,
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                )
            )
            self._session.flush()
        return identifier

    def _assert_literal(
        self,
        tenant_id: str,
        label: str,
        *,
        subject_entity_id: UUID,
        predicate: str,
        object_value: str,
        source_system_id: UUID,
    ) -> int:
        del tenant_id
        assertion_id = self._demo_id(f"assertion:{label}")
        if self._session.get(Assertion, assertion_id) is not None:
            return 0
        self._session.add(
            Assertion(
                assertion_id=assertion_id,
                assertion_name=f"Gate F demo: {label}",
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                subject_entity_id=subject_entity_id,
                predicate=predicate,
                object_value=object_value,
                object_entity_id=None,
                source_system_id=source_system_id,
                source_object_id=None,
                asserted_on=SEED_TIMESTAMP,
                assertion_type="Evidence-backed",
                relationship_type_id=None,
            )
        )
        self._session.flush()
        return 1


if __name__ == "__main__":
    from app.core.config import get_settings
    from app.infrastructure.persistence.database import create_database_engine
    from app.infrastructure.persistence.session import create_session_factory

    settings = get_settings()
    engine = create_database_engine(settings)
    sessions = create_session_factory(engine)
    with sessions.begin() as cli_session:
        result = DemoGateFSeeder(cli_session).seed()
    print(result)
