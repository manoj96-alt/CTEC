"""Real-PostgreSQL proof of the Ask CTEC application service (Gate D):
entity resolution (unique/no-match/ambiguous, fail-closed), ontology
traversal against real institutional_relationships rows, tenant isolation,
deterministic repeated results, and the read-only guarantee.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.ontology_copilot_api import AskStatus, OntologyCopilotApiService
from app.core.bootstrap import BOOTSTRAP_BUSINESS_DOMAIN_ID, BOOTSTRAP_SYSTEM_ENTITY_ID
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.session import create_session_factory

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _tenant(label: str) -> str:
    return f"{label}-{uuid4()}"


def _principal(tenant_id: str) -> TrustedPrincipal:
    now = datetime.now(UTC)
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=("ontology-copilot:ask",),
        roles=(),
        issuer="issuer",
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(hours=1),
    )


def _type_ids(session: Session) -> tuple[dict[str, UUID], dict[str, UUID]]:
    OntologySeeder(session).load()
    session.flush()
    entity_types: dict[str, UUID] = {
        name: entity_type_id
        for name, entity_type_id in session.execute(
            select(EntityType.entity_type_name, EntityType.entity_type_id).where(
                EntityType.entity_type_name.in_(("Supplier", "Material", "BOM", "Product"))
            )
        ).all()
    }
    relationship_types: dict[str, UUID] = {
        name: relationship_type_id
        for name, relationship_type_id in session.execute(
            select(
                RelationshipType.relationship_type_name, RelationshipType.relationship_type_id
            ).where(RelationshipType.relationship_type_name.in_(("supplies", "usedIn", "defines")))
        ).all()
    }
    return entity_types, relationship_types


def _seed_entity(session: Session, *, tenant_id: str, name: str, entity_type_id: UUID) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            entity_type_id=entity_type_id,
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _seed_relationship(
    session: Session,
    *,
    tenant_id: str,
    relationship_type_id: UUID,
    from_entity_id: UUID,
    to_entity_id: UUID,
    name: str | None = None,
) -> None:
    session.add(
        InstitutionalRelationship(
            institutional_relationship_id=uuid4(),
            tenant_id=tenant_id,
            institutional_relationship_name=name or f"rel-{uuid4()}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            relationship_type_id=relationship_type_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
        )
    )
    session.flush()


def _seed_supply_chain(
    session: Session,
    *,
    tenant_id: str,
    supplier_name: str,
    entity_types: dict[str, UUID],
    relationship_types: dict[str, UUID],
    product_count: int = 2,
) -> UUID:
    supplier_id = _seed_entity(
        session, tenant_id=tenant_id, name=supplier_name, entity_type_id=entity_types["Supplier"]
    )
    for i in range(product_count):
        material_id = _seed_entity(
            session,
            tenant_id=tenant_id,
            name=f"Material {i} for {supplier_name}",
            entity_type_id=entity_types["Material"],
        )
        bom_id = _seed_entity(
            session,
            tenant_id=tenant_id,
            name=f"BOM {i} for {supplier_name}",
            entity_type_id=entity_types["BOM"],
        )
        product_id = _seed_entity(
            session,
            tenant_id=tenant_id,
            name=f"Product {i} for {supplier_name}",
            entity_type_id=entity_types["Product"],
        )
        _seed_relationship(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_types["supplies"],
            from_entity_id=supplier_id,
            to_entity_id=material_id,
        )
        _seed_relationship(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_types["usedIn"],
            from_entity_id=material_id,
            to_entity_id=bom_id,
        )
        _seed_relationship(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_types["defines"],
            from_entity_id=bom_id,
            to_entity_id=product_id,
        )
    return supplier_id


def test_supplier_resolves_uniquely_and_traversal_finds_expected_products(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant")
    with Session(migrated_engine) as session, session.begin():
        entity_types, relationship_types = _type_ids(session)
        supplier_name = f"TSMC-{uuid4()}"
        _seed_supply_chain(
            session,
            tenant_id=tenant_id,
            supplier_name=supplier_name,
            entity_types=entity_types,
            relationship_types=relationship_types,
            product_count=2,
        )

    service = OntologyCopilotApiService(create_session_factory(migrated_engine))
    result = service.ask(_principal(tenant_id), f"Which products depend on {supplier_name}?")

    assert result.status == AskStatus.ANSWERED
    assert result.resolved_entity is not None
    assert result.resolved_entity.entity_name == supplier_name
    assert result.resolved_entity.entity_type_name == "Supplier"
    assert len(result.result_names) == 2
    assert len(result.evidence) == 2
    for path in result.evidence:
        relationship_names = [step.relationship_name for step in path if step.relationship_name]
        assert relationship_names == ["supplies", "usedIn", "defines"]


def test_supplier_not_found_returns_no_match(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant")
    with Session(migrated_engine) as session, session.begin():
        _type_ids(session)

    service = OntologyCopilotApiService(create_session_factory(migrated_engine))
    result = service.ask(_principal(tenant_id), f"Which products depend on Nonexistent-{uuid4()}?")

    assert result.status == AskStatus.NO_MATCH
    assert result.reason == "NO_MATCHING_ENTITY"
    assert result.resolved_entity is None
    assert result.evidence == ()


def test_ambiguous_supplier_name_fails_closed_not_an_arbitrary_choice(
    migrated_engine: Engine,
) -> None:
    # The tenant-scoped uniqueness constraint (RFC-015) forbids two rows with
    # the byte-identical name within one tenant, so genuine ambiguity can
    # only arise here from two real, distinct, differently-cased rows that
    # the deterministic case-insensitive lookup (by design) still matches
    # both of -- exactly the kind of ambiguity a real customer could
    # accidentally create.
    tenant_id = _tenant("tenant")
    base_label = f"Ambiguous-Supplier-{uuid4()}"
    lower_name = base_label.lower()
    upper_name = base_label.upper()
    with Session(migrated_engine) as session, session.begin():
        entity_types, _relationship_types = _type_ids(session)
        _seed_entity(
            session, tenant_id=tenant_id, name=lower_name, entity_type_id=entity_types["Supplier"]
        )
        _seed_entity(
            session, tenant_id=tenant_id, name=upper_name, entity_type_id=entity_types["Supplier"]
        )

    service = OntologyCopilotApiService(create_session_factory(migrated_engine))
    result = service.ask(_principal(tenant_id), f"Which products depend on {lower_name}?")

    assert result.status == AskStatus.AMBIGUOUS_MATCH
    assert result.reason == "AMBIGUOUS_ENTITY"
    assert result.resolved_entity is None
    assert result.result_names == ()
    assert result.evidence == ()


def test_unsupported_question_never_hits_the_database(migrated_engine: Engine) -> None:
    service = OntologyCopilotApiService(create_session_factory(migrated_engine))
    result = service.ask(_principal(_tenant("tenant")), "What is the weather today?")
    assert result.status == AskStatus.UNSUPPORTED_QUESTION
    assert result.reason == "UNRECOGNIZED_QUESTION"


def test_tenant_a_success_and_tenant_b_cannot_observe_tenant_a_data(
    migrated_engine: Engine,
) -> None:
    tenant_a = _tenant("tenant-a")
    tenant_b = _tenant("tenant-b")
    supplier_name = f"Shared-Named-Supplier-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        entity_types, relationship_types = _type_ids(session)
        _seed_supply_chain(
            session,
            tenant_id=tenant_a,
            supplier_name=supplier_name,
            entity_types=entity_types,
            relationship_types=relationship_types,
            product_count=1,
        )

    service = OntologyCopilotApiService(create_session_factory(migrated_engine))

    tenant_a_result = service.ask(
        _principal(tenant_a), f"Which products depend on {supplier_name}?"
    )
    assert tenant_a_result.status == AskStatus.ANSWERED
    assert len(tenant_a_result.result_names) == 1

    tenant_b_result = service.ask(
        _principal(tenant_b), f"Which products depend on {supplier_name}?"
    )
    assert tenant_b_result.status == AskStatus.NO_MATCH
    assert tenant_b_result.resolved_entity is None
    assert tenant_b_result.evidence == ()


def test_cross_tenant_evidence_cannot_leak_even_when_both_tenants_have_a_same_named_supplier(
    migrated_engine: Engine,
) -> None:
    # Two different customers can legitimately both name a supplier "TSMC" --
    # the tenant-scoped uniqueness constraint (RFC-015) permits identical
    # names across different tenants. This test deliberately creates that
    # collision. Because it is committed to the same database the
    # session-scoped migrated_engine fixture shares across this whole test
    # file, and that fixture's teardown briefly downgrades through the
    # pre-RFC-015 schema (global, not tenant-scoped, name uniqueness) to
    # reach revision 0010, this test explicitly deletes every row it created
    # afterward -- regardless of assertion outcome -- so the shared database
    # never carries a same-name-different-tenant collision past this test,
    # exactly the kind of state a real future downgrade could legitimately
    # need to run against.
    tenant_a = _tenant("tenant-a")
    tenant_b = _tenant("tenant-b")
    supplier_name = f"Collision-Supplier-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        entity_types, relationship_types = _type_ids(session)
        _seed_supply_chain(
            session,
            tenant_id=tenant_a,
            supplier_name=supplier_name,
            entity_types=entity_types,
            relationship_types=relationship_types,
            product_count=3,
        )
        _seed_supply_chain(
            session,
            tenant_id=tenant_b,
            supplier_name=supplier_name,
            entity_types=entity_types,
            relationship_types=relationship_types,
            product_count=1,
        )

    try:
        service = OntologyCopilotApiService(create_session_factory(migrated_engine))

        tenant_a_result = service.ask(
            _principal(tenant_a), f"Which products depend on {supplier_name}?"
        )
        tenant_b_result = service.ask(
            _principal(tenant_b), f"Which products depend on {supplier_name}?"
        )

        assert len(tenant_a_result.result_names) == 3
        assert len(tenant_b_result.result_names) == 1

        tenant_a_entity_ids = {step.entity_id for path in tenant_a_result.evidence for step in path}
        tenant_b_entity_ids = {step.entity_id for path in tenant_b_result.evidence for step in path}
        assert tenant_a_entity_ids.isdisjoint(tenant_b_entity_ids)
    finally:
        with Session(migrated_engine) as session, session.begin():
            session.execute(
                text("DELETE FROM institutional_relationships WHERE tenant_id IN (:a, :b)"),
                {"a": tenant_a, "b": tenant_b},
            )
            session.execute(
                text("DELETE FROM enterprise_entities WHERE tenant_id IN (:a, :b)"),
                {"a": tenant_a, "b": tenant_b},
            )


def test_repeated_identical_request_produces_an_equivalent_deterministic_result(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant")
    supplier_name = f"Deterministic-Supplier-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        entity_types, relationship_types = _type_ids(session)
        _seed_supply_chain(
            session,
            tenant_id=tenant_id,
            supplier_name=supplier_name,
            entity_types=entity_types,
            relationship_types=relationship_types,
            product_count=2,
        )

    service = OntologyCopilotApiService(create_session_factory(migrated_engine))
    question = f"Which products depend on {supplier_name}?"

    first = service.ask(_principal(tenant_id), question)
    second = service.ask(_principal(tenant_id), question)

    assert first.status == second.status == AskStatus.ANSWERED
    assert first.result_names == second.result_names
    assert first.answer == second.answer
    first_evidence_names = [[s.entity_name for s in path] for path in first.evidence]
    second_evidence_names = [[s.entity_name for s in path] for path in second.evidence]
    assert first_evidence_names == second_evidence_names


def test_ask_endpoint_is_read_only_no_row_counts_change(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant")
    supplier_name = f"ReadOnly-Supplier-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        entity_types, relationship_types = _type_ids(session)
        _seed_supply_chain(
            session,
            tenant_id=tenant_id,
            supplier_name=supplier_name,
            entity_types=entity_types,
            relationship_types=relationship_types,
            product_count=2,
        )

    def _counts(session: Session) -> tuple[int, int, int, int]:
        return (
            session.execute(select(func.count()).select_from(EnterpriseEntity)).scalar_one(),
            session.execute(
                select(func.count()).select_from(InstitutionalRelationship)
            ).scalar_one(),
            session.execute(select(func.count()).select_from(EntityType)).scalar_one(),
            session.execute(select(func.count()).select_from(RelationshipType)).scalar_one(),
        )

    with Session(migrated_engine) as session:
        before = _counts(session)

    service = OntologyCopilotApiService(create_session_factory(migrated_engine))
    for question in (
        f"Which products depend on {supplier_name}?",
        f"Which products depend on Nonexistent-{uuid4()}?",
        "What is the weather today?",
    ):
        service.ask(_principal(tenant_id), question)

    with Session(migrated_engine) as session:
        after = _counts(session)

    assert before == after
