"""Explicit, idempotent, demo-only seeder for the Ask CTEC demonstration
scenario (Gate D, Priority 6).

Never invoked by normal production bootstrap: app.main.lifespan only ever
builds the dependency Container (see app/main.py) -- nothing there, or
anywhere else on the request path, calls this module. It has its own,
separate, manually-run CLI entrypoint (see __main__ below) and must be
invoked deliberately.

Refuses to seed any tenant other than the labeled demo tenant
(BOOTSTRAP_DEMO_TENANT_ID). Persists one governed instance-level supply chain
through the real, authorized mechanism -- institutional_relationships,
tenant-scoped per RFC-016 (architecture/released/v1.9/) -- connecting a
clearly-labeled fictional "TSMC" supplier entity to two products through two
independent Material -> BOM -> Product chains, using the real ontology
relationship types (supplies/usedIn/defines) already governed by
app.infrastructure.persistence.ontology_seed:

    TSMC --supplies--> Material A --usedIn--> BOM A --defines--> Product A
    TSMC --supplies--> Material B --usedIn--> BOM B --defines--> Product B

Calls OntologySeeder.load() first (idempotent, safe to call repeatedly) to
guarantee the Supplier/Material/BOM/Product entity types and
supplies/usedIn/defines relationship types this seeder depends on already
exist, regardless of invocation order.

Idempotent: every id used is deterministic (uuid5, namespaced under the
existing BOOTSTRAP_SEED_NAMESPACE), and every write is preceded by an
existence check, so running seed() twice against the same database creates
nothing new the second time.
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
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.ontology_seed import OntologySeeder

SUPPLIER_NAME = "TSMC"


def _demo_id(label: str) -> UUID:
    """Deterministic id for a fixed demo label: re-running the seeder
    against the same database always derives the same ids, making the
    existence checks below meaningful (idempotency)."""
    return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"ontology-copilot-demo:{label}")


_SUPPLIER_ENTITY_ID = _demo_id("enterprise-entity:tsmc")
_MATERIAL_A_ENTITY_ID = _demo_id("enterprise-entity:material-a")
_MATERIAL_B_ENTITY_ID = _demo_id("enterprise-entity:material-b")
_BOM_A_ENTITY_ID = _demo_id("enterprise-entity:bom-a")
_BOM_B_ENTITY_ID = _demo_id("enterprise-entity:bom-b")
_PRODUCT_A_ENTITY_ID = _demo_id("enterprise-entity:product-a")
_PRODUCT_B_ENTITY_ID = _demo_id("enterprise-entity:product-b")

_REL_SUPPLIER_MATERIAL_A_ID = _demo_id("institutional-relationship:supplies:a")
_REL_SUPPLIER_MATERIAL_B_ID = _demo_id("institutional-relationship:supplies:b")
_REL_MATERIAL_BOM_A_ID = _demo_id("institutional-relationship:usedin:a")
_REL_MATERIAL_BOM_B_ID = _demo_id("institutional-relationship:usedin:b")
_REL_BOM_PRODUCT_A_ID = _demo_id("institutional-relationship:defines:a")
_REL_BOM_PRODUCT_B_ID = _demo_id("institutional-relationship:defines:b")


class DemoTenantRequiredError(Exception):
    """Raised when the seeder is asked to seed any tenant other than the
    labeled demo tenant."""


@dataclass(frozen=True, slots=True)
class DemoEntitySeedResult:
    entity_id: UUID
    created: bool


@dataclass(frozen=True, slots=True)
class DemoOntologyCopilotSeedSummary:
    tenant_id: str
    supplier: DemoEntitySeedResult
    products: tuple[DemoEntitySeedResult, ...]
    relationships_created: int


class DemoOntologyCopilotSeeder:
    """Test-covered in test_demo_ontology_copilot_seeder.py and
    test_demo_ontology_copilot_seeder_postgres.py."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def seed(self, tenant_id: str = BOOTSTRAP_DEMO_TENANT_ID) -> DemoOntologyCopilotSeedSummary:
        if tenant_id != BOOTSTRAP_DEMO_TENANT_ID:
            raise DemoTenantRequiredError(
                f"The demo Ask CTEC seeder refuses to seed tenant {tenant_id!r}; "
                f"it only ever seeds the labeled demo tenant {BOOTSTRAP_DEMO_TENANT_ID!r}."
            )

        OntologySeeder(self._session).load()
        self._session.flush()

        entity_type_ids = self._entity_type_ids_by_name(("Supplier", "Material", "BOM", "Product"))
        relationship_type_ids = self._relationship_type_ids_by_name(
            ("supplies", "usedIn", "defines")
        )

        supplier = self._seed_enterprise_entity(
            tenant_id, _SUPPLIER_ENTITY_ID, SUPPLIER_NAME, entity_type_ids["Supplier"]
        )
        # Returned results are not needed individually here: the fixed
        # _MATERIAL_A_ENTITY_ID/_BOM_A_ENTITY_ID/... constants (not these
        # method return values) are what the relationship-seeding loop below
        # references, exactly as _seed_enterprise_entity's own existence
        # check keys off of.
        self._seed_enterprise_entity(
            tenant_id,
            _MATERIAL_A_ENTITY_ID,
            "Demo Material A (TSMC)",
            entity_type_ids["Material"],
        )
        self._seed_enterprise_entity(
            tenant_id,
            _MATERIAL_B_ENTITY_ID,
            "Demo Material B (TSMC)",
            entity_type_ids["Material"],
        )
        self._seed_enterprise_entity(
            tenant_id, _BOM_A_ENTITY_ID, "Demo BOM A", entity_type_ids["BOM"]
        )
        self._seed_enterprise_entity(
            tenant_id, _BOM_B_ENTITY_ID, "Demo BOM B", entity_type_ids["BOM"]
        )
        product_a = self._seed_enterprise_entity(
            tenant_id, _PRODUCT_A_ENTITY_ID, "Demo Product A", entity_type_ids["Product"]
        )
        product_b = self._seed_enterprise_entity(
            tenant_id, _PRODUCT_B_ENTITY_ID, "Demo Product B", entity_type_ids["Product"]
        )
        self._session.flush()

        relationships_created = 0
        for relationship_id, name, relationship_type_name, from_id, to_id in (
            (
                _REL_SUPPLIER_MATERIAL_A_ID,
                "Demo: TSMC supplies Material A",
                "supplies",
                _SUPPLIER_ENTITY_ID,
                _MATERIAL_A_ENTITY_ID,
            ),
            (
                _REL_SUPPLIER_MATERIAL_B_ID,
                "Demo: TSMC supplies Material B",
                "supplies",
                _SUPPLIER_ENTITY_ID,
                _MATERIAL_B_ENTITY_ID,
            ),
            (
                _REL_MATERIAL_BOM_A_ID,
                "Demo: Material A used in BOM A",
                "usedIn",
                _MATERIAL_A_ENTITY_ID,
                _BOM_A_ENTITY_ID,
            ),
            (
                _REL_MATERIAL_BOM_B_ID,
                "Demo: Material B used in BOM B",
                "usedIn",
                _MATERIAL_B_ENTITY_ID,
                _BOM_B_ENTITY_ID,
            ),
            (
                _REL_BOM_PRODUCT_A_ID,
                "Demo: BOM A defines Product A",
                "defines",
                _BOM_A_ENTITY_ID,
                _PRODUCT_A_ENTITY_ID,
            ),
            (
                _REL_BOM_PRODUCT_B_ID,
                "Demo: BOM B defines Product B",
                "defines",
                _BOM_B_ENTITY_ID,
                _PRODUCT_B_ENTITY_ID,
            ),
        ):
            if self._seed_institutional_relationship(
                tenant_id,
                relationship_id,
                name,
                relationship_type_ids[relationship_type_name],
                from_id,
                to_id,
            ):
                relationships_created += 1

        return DemoOntologyCopilotSeedSummary(
            tenant_id=tenant_id,
            supplier=supplier,
            products=(product_a, product_b),
            relationships_created=relationships_created,
        )

    def _entity_type_ids_by_name(self, names: tuple[str, ...]) -> dict[str, UUID]:
        rows = self._session.execute(
            select(EntityType.entity_type_name, EntityType.entity_type_id).where(
                EntityType.entity_type_name.in_(names)
            )
        ).all()
        found = {name: entity_type_id for name, entity_type_id in rows}
        missing = set(names) - set(found)
        if missing:
            raise RuntimeError(
                f"Demo Ask CTEC seeder: required entity type(s) not found after "
                f"OntologySeeder.load(): {sorted(missing)}"
            )
        return found

    def _relationship_type_ids_by_name(self, names: tuple[str, ...]) -> dict[str, UUID]:
        rows = self._session.execute(
            select(
                RelationshipType.relationship_type_name, RelationshipType.relationship_type_id
            ).where(RelationshipType.relationship_type_name.in_(names))
        ).all()
        found = {name: relationship_type_id for name, relationship_type_id in rows}
        missing = set(names) - set(found)
        if missing:
            raise RuntimeError(
                f"Demo Ask CTEC seeder: required relationship type(s) not found after "
                f"OntologySeeder.load(): {sorted(missing)}"
            )
        return found

    def _seed_enterprise_entity(
        self, tenant_id: str, entity_id: UUID, name: str, entity_type_id: UUID
    ) -> DemoEntitySeedResult:
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
        return DemoEntitySeedResult(entity_id=entity_id, created=True)

    def _seed_institutional_relationship(
        self,
        tenant_id: str,
        relationship_id: UUID,
        name: str,
        relationship_type_id: UUID,
        from_entity_id: UUID,
        to_entity_id: UUID,
    ) -> bool:
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
        return True


if __name__ == "__main__":
    from app.core.config import get_settings
    from app.infrastructure.persistence.database import create_database_engine
    from app.infrastructure.persistence.session import create_session_factory

    settings = get_settings()
    engine = create_database_engine(settings)
    sessions = create_session_factory(engine)
    with sessions.begin() as cli_session:
        result = DemoOntologyCopilotSeeder(cli_session).seed()
    print(result)
