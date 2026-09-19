"""Explicit, idempotent, demo-only seeder for the Gate F Supply Chain
Impact demonstration scenarios (F-I4, governed by the merged CDD-015
Deterministic Demo Data and Read-Projection Clarification and
Remediation Report; topology corrected per CDD-088's Alternative Sourcing
Semantics Governance Correction).

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
alongside the seven pre-existing ones, plus CDD-088's one additive
relationship type (approvedSourceFor):

    RECOMMENDED scenario:
        Supplier A (R) --locatedIn--> Region(R) --exposedTo--> RiskEvent(R,
        severity=Severe)
        Supplier A (R) --supplies--> Material M (R) -- the ONE, SOLE,
        currently-ACTIVE source (CDD-088 §1/§5: `supplies` means active,
        current sourcing, and is the exact signal
        krm.py::derive_single_source_exposure counts for condition 2 --
        never touched by anything below).
        Material M (R) --usedIn--> BOM(R) --defines--> Product(R)
            --assembledAt--> Facility(R)
        Product(R) --generatesRevenue--> RevenueExposure(R,
        annualRevenueUsd=12,000,000)

        Candidate B (ordinary Supplier) --approvedSourceFor--> Material M
        (R) -- a governed, durable sourcing-CAPABILITY fact, NOT an
        active-sourcing fact (CDD-088 §4) -- with qualification=true,
        capacity=true, leadTimeDays=21, costUsd=185000: RELEVANT and
        fully ELIGIBLE -> Recommended.

        Candidate C (ordinary Supplier) --approvedSourceFor--> Material M
        (R), with qualification=true but NO capacity assertion at all
        (genuinely absent, never asserted false): RELEVANT (a real
        governed `approvedSourceFor` relationship makes it a candidate)
        while its capacity/eligibility remains truthfully UNKNOWN.
        Proves "relevant candidate != eligible candidate."

        Candidate E (ordinary Supplier) --approvedSourceFor--> Material M
        (R), with qualification=true but capacity=false (an EXPLICIT,
        real, persisted governed fact -- never invented policy):
        RELEVANT but FAILS the existing capacity condition ->
        Rejected: candidate capacity is insufficient. Proves "relevant
        candidate != passing candidate," using Gate F's own existing
        REJECTED_INSUFFICIENT_CAPACITY reason, never a new one.

        Unrelated Supplier D (ordinary Supplier) --approvedSourceFor-->
        Unrelated Material X (R) -- a real Supplier with a real
        `approvedSourceFor` edge, but never to Material M, so it must
        never appear in this scenario's candidate set.

        None of B/C/E/D ever has a `supplies` edge to Material M --
        Material M's only currently-active `supplies` relationship
        remains Supplier A's, so `single_source_exposure` stays TRUE
        throughout, regardless of how many `approvedSourceFor` candidates
        exist or how their evidence varies (CDD-088 §5/§18).

    UNKNOWN scenario:
        Same shape, its own Region/RiskEvent/Material/Candidate -- but the
        RiskEvent carries NO severity assertion (evidence genuinely
        absent, never asserted false). Its one candidate
        (--approvedSourceFor-->) is fully qualified/capacitated;
        irrelevant to the outcome, since condition 1 (severity) is
        already Unknown regardless of candidate evidence.

    REJECTED scenario:
        Same shape, its own Region/RiskEvent (severity=Severe)/Material/
        Candidate -- but its RevenueExposure carries annualRevenueUsd=
        5,000,000 (asserted, real, below the frozen $10,000,000
        materiality threshold). Rejected via the governed
        REJECTED_NOT_MATERIAL path (GateFDecisionAdapter._classify,
        backend/app/integration/adapters/gate_f/drm.py), which
        short-circuits ahead of any candidate check -- this scenario's one
        candidate (--approvedSourceFor-->) is fully qualified/capacitated
        and irrelevant to the outcome for the same reason.

    Candidate discovery itself is a material-aware, relationship-driven
    derivation, never a tenant-wide "Alternate Supplier" entity-type scan
    (CDD-086 §1-§2's diagnosed defect) and never a reuse of `supplies`
    (CDD-088 §1's diagnosed defect -- reusing the active-sourcing signal
    for discovery would make discovering ANY candidate falsify
    single-source exposure). Each scenario's candidates are ordinary
    Supplier entities, discoverable solely via their real
    `approvedSourceFor` relationship into that scenario's own Material
    (backend/app/domain/ontology_copilot/traversal.py::
    discover_candidates_supplying, called per-material by
    backend/app/application/supply_chain_impact_api.py). Because
    discovery is material-scoped, each scenario seeds its own independent
    candidate(s) -- no candidate is, or needs to be, shared across
    scenarios.

    No seeded field or relationship anywhere below encodes an expected
    outcome, a winner, or a candidate list directly -- every discoverable
    candidate, and every governed result Gate F produces for it, is a
    derived consequence of the real `supplies`/`approvedSourceFor`
    relationships and real assertions seeded here (CDD-088 §7 standing
    synthetic-data rule).

Calls OntologySeeder(session).load() first (idempotent) to guarantee every
entity type and relationship type this seeder depends on already exists,
regardless of invocation order. The "Alternate Supplier" entity type
remains defined by OntologySeeder for backward compatibility (CDD-087
§6) -- this seeder simply no longer creates an instance of it or relies
on its type name for discovery. `candidateFor` remains untouched here --
it is created only at evaluation time, by Gate F's own KRM
(krm.py::derive_candidate_evidence), never by this seeder.

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
    AZURE_DEV_DEMO_TENANT_ID,
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    SEED_TIMESTAMP,
)

_ALLOWED_SEED_TENANTS = (BOOTSTRAP_DEMO_TENANT_ID, AZURE_DEV_DEMO_TENANT_ID)
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
)
_REQUIRED_RELATIONSHIP_TYPES = (
    "supplies",
    "usedIn",
    "defines",
    "assembledAt",
    "generatesRevenue",
    "locatedIn",
    "exposedTo",
    "approvedSourceFor",
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
    # Ordinary Supplier entities discoverable as candidates for this
    # scenario's own material via a real `approvedSourceFor` relationship
    # (CDD-088) -- never a seeded answer, a consequence of the
    # relationships seeded below.
    candidate_supplier_entity_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class DemoGateFSeedSummary:
    tenant_id: str
    source_system_id: UUID
    recommended: DemoGateFScenarioSummary
    unknown: DemoGateFScenarioSummary
    rejected: DemoGateFScenarioSummary
    relationships_created: int
    assertions_created: int


class DemoGateFSeeder:
    """Test-covered in test_demo_gate_f_seeder.py and
    test_demo_gate_f_seeder_postgres.py."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def seed(self, tenant_id: str = BOOTSTRAP_DEMO_TENANT_ID) -> DemoGateFSeedSummary:
        if tenant_id not in _ALLOWED_SEED_TENANTS:
            raise DemoTenantRequiredError(
                f"The demo Gate F seeder refuses to seed tenant {tenant_id!r}; "
                f"it only ever seeds one of the explicitly labeled tenants "
                f"{_ALLOWED_SEED_TENANTS!r}."
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

        # Candidate B: relevant AND fully eligible -> Recommended.
        candidate_b_id, created, asserted = self._seed_candidate(
            tenant_id,
            scenario_label="recommended",
            suffix="candidate-b",
            name="Demo Candidate Supplier B (recommended)",
            material_entity_id=recommended.material_entity_id,
            supplier_type_id=entity_type_ids["Supplier"],
            approved_source_for_relationship_type_id=relationship_type_ids["approvedSourceFor"],
            source_system_id=supplier_source_id,
            qualification="true",
            capacity="true",
            lead_time_days="21",
            cost_usd="185000",
        )
        relationships_created += created
        assertions_created += asserted

        # Candidate C: relevant (real `approvedSourceFor` edge to the same
        # Material) but capacity is genuinely never asserted -- proves
        # relevance survives missing eligibility evidence; Gate F must
        # evaluate this candidate as UNKNOWN on capacity, never False,
        # never absent from the response.
        candidate_c_id, created, asserted = self._seed_candidate(
            tenant_id,
            scenario_label="recommended",
            suffix="candidate-c",
            name="Demo Candidate Supplier C (recommended)",
            material_entity_id=recommended.material_entity_id,
            supplier_type_id=entity_type_ids["Supplier"],
            approved_source_for_relationship_type_id=relationship_type_ids["approvedSourceFor"],
            source_system_id=supplier_source_id,
            qualification="true",
            capacity=None,
            lead_time_days="35",
            cost_usd="170000",
        )
        relationships_created += created
        assertions_created += asserted

        # Candidate E: relevant (real `approvedSourceFor` edge) but an
        # EXISTING governed condition is explicitly, persistently FALSE
        # (capacity=false, a real asserted fact -- never invented policy)
        # -> Rejected: candidate capacity is insufficient
        # (GateFOutcomeReason.REJECTED_INSUFFICIENT_CAPACITY, unchanged).
        # Proves "relevant candidate != passing candidate."
        candidate_e_id, created, asserted = self._seed_candidate(
            tenant_id,
            scenario_label="recommended",
            suffix="candidate-e",
            name="Demo Candidate Supplier E (recommended)",
            material_entity_id=recommended.material_entity_id,
            supplier_type_id=entity_type_ids["Supplier"],
            approved_source_for_relationship_type_id=relationship_type_ids["approvedSourceFor"],
            source_system_id=supplier_source_id,
            qualification="true",
            capacity="false",
            lead_time_days="45",
            cost_usd="200000",
        )
        relationships_created += created
        assertions_created += asserted

        # Unrelated Supplier: a real Supplier with a real
        # `approvedSourceFor` relationship, but to a different Material
        # entirely -- must never appear in `recommended`'s candidate set
        # (material-aware relevance: an ordinary Supplier approved only
        # for an unrelated Material is not discovered for this one).
        unrelated_material = self._entity(
            tenant_id,
            "gate-f-demo:recommended:unrelated-material",
            "Demo Unrelated Material (recommended)",
            entity_type_ids["Material"],
        )
        _unrelated_supplier_id, created, asserted = self._seed_candidate(
            tenant_id,
            scenario_label="recommended",
            suffix="unrelated-supplier",
            name="Demo Unrelated Supplier (recommended)",
            material_entity_id=unrelated_material.entity_id,
            supplier_type_id=entity_type_ids["Supplier"],
            approved_source_for_relationship_type_id=relationship_type_ids["approvedSourceFor"],
            source_system_id=supplier_source_id,
            qualification="true",
            capacity="true",
            lead_time_days="14",
            cost_usd="150000",
        )
        relationships_created += created
        assertions_created += asserted

        recommended = DemoGateFScenarioSummary(
            supplier_entity_id=recommended.supplier_entity_id,
            material_entity_id=recommended.material_entity_id,
            risk_event_entity_id=recommended.risk_event_entity_id,
            candidate_supplier_entity_ids=(candidate_b_id, candidate_c_id, candidate_e_id),
        )

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
        unknown_candidate_id, created, asserted = self._seed_candidate(
            tenant_id,
            scenario_label="unknown",
            suffix="candidate",
            name="Demo Candidate Supplier (unknown)",
            material_entity_id=unknown.material_entity_id,
            supplier_type_id=entity_type_ids["Supplier"],
            approved_source_for_relationship_type_id=relationship_type_ids["approvedSourceFor"],
            source_system_id=supplier_source_id,
            qualification="true",
            capacity="true",
            lead_time_days="21",
            cost_usd="185000",
        )
        relationships_created += created
        assertions_created += asserted
        unknown = DemoGateFScenarioSummary(
            supplier_entity_id=unknown.supplier_entity_id,
            material_entity_id=unknown.material_entity_id,
            risk_event_entity_id=unknown.risk_event_entity_id,
            candidate_supplier_entity_ids=(unknown_candidate_id,),
        )

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
        rejected_candidate_id, created, asserted = self._seed_candidate(
            tenant_id,
            scenario_label="rejected",
            suffix="candidate",
            name="Demo Candidate Supplier (rejected)",
            material_entity_id=rejected.material_entity_id,
            supplier_type_id=entity_type_ids["Supplier"],
            approved_source_for_relationship_type_id=relationship_type_ids["approvedSourceFor"],
            source_system_id=supplier_source_id,
            qualification="true",
            capacity="true",
            lead_time_days="21",
            cost_usd="185000",
        )
        relationships_created += created
        assertions_created += asserted
        rejected = DemoGateFScenarioSummary(
            supplier_entity_id=rejected.supplier_entity_id,
            material_entity_id=rejected.material_entity_id,
            risk_event_entity_id=rejected.risk_event_entity_id,
            candidate_supplier_entity_ids=(rejected_candidate_id,),
        )

        return DemoGateFSeedSummary(
            tenant_id=tenant_id,
            source_system_id=source_system_id,
            recommended=recommended,
            unknown=unknown,
            rejected=rejected,
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
        # `supplies` here is the material's ONE, SOLE, currently-active
        # source -- the only `supplies` edge this seeder ever creates
        # into this material (CDD-088 §1/§18). Every candidate below uses
        # `approvedSourceFor` instead, never `supplies`.
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

        # `candidate_supplier_entity_ids` is filled in by the caller once
        # this scenario's candidate(s) are seeded (they need
        # `material.entity_id`, produced here) -- left empty in this
        # intermediate summary.
        summary = DemoGateFScenarioSummary(
            supplier_entity_id=supplier.entity_id,
            material_entity_id=material.entity_id,
            risk_event_entity_id=risk_event.entity_id,
            candidate_supplier_entity_ids=(),
        )
        return summary, relationships_created, assertions_created

    def _seed_candidate(
        self,
        tenant_id: str,
        *,
        scenario_label: str,
        suffix: str,
        name: str,
        material_entity_id: UUID,
        supplier_type_id: UUID,
        approved_source_for_relationship_type_id: UUID,
        source_system_id: UUID,
        qualification: str | None,
        capacity: str | None,
        lead_time_days: str | None,
        cost_usd: str | None,
    ) -> tuple[UUID, int, int]:
        """Seeds one ordinary Supplier entity with a real
        `approvedSourceFor` relationship into `material_entity_id` -- the
        sole discovery/relevance signal (CDD-088 §4/§6). Deliberately
        NEVER `supplies` -- that relationship means active, current
        sourcing and is the exact signal
        krm.py::derive_single_source_exposure counts; giving a candidate a
        `supplies` edge would falsify single-source exposure the moment
        any candidate exists. No entity type other than `Supplier` is
        used; relevance is entirely a consequence of the
        `approvedSourceFor` edge, never of typing. A `None` or explicit
        `"false"` evidence value is asserted exactly as given -- never
        silently changed -- so a candidate can be relevant while a
        specific eligibility fact remains truthfully Unknown (`None`) or
        truthfully failing (`"false"`)."""
        label = f"gate-f-demo:{scenario_label}:{suffix}"
        candidate = self._entity(tenant_id, label, name, supplier_type_id)
        relationships_created = 0
        if self._relate(
            tenant_id,
            f"{label}:approved-source-for",
            f"Demo: approvedSourceFor ({scenario_label}:{suffix})",
            approved_source_for_relationship_type_id,
            candidate.entity_id,
            material_entity_id,
        ):
            relationships_created += 1

        assertions_created = 0
        for predicate, value in (
            ("qualification", qualification),
            ("capacity", capacity),
            ("leadTimeDays", lead_time_days),
            ("costUsd", cost_usd),
        ):
            if value is None:
                continue
            assertions_created += self._assert_literal(
                tenant_id,
                f"{label}:{predicate}",
                subject_entity_id=candidate.entity_id,
                predicate=predicate,
                object_value=value,
                source_system_id=source_system_id,
            )
        return candidate.entity_id, relationships_created, assertions_created

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
