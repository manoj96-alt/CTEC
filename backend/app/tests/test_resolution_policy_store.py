from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.domain.identity_resolution.policy import conservative_preset
from app.infrastructure.persistence.models.resolution_policy import ResolutionPolicyModel
from app.infrastructure.persistence.resolution_policy_store import (
    BUILT_IN_PRESETS,
    ResolutionPolicyStore,
)


def _tenant() -> str:
    # A tenant id unique to this test run: migrated_engine is a session-scoped
    # fixture shared with other test modules.
    return f"tenant-policy-{uuid4()}"


def test_materialize_creates_a_tenant_owned_row(migrated_engine: Engine) -> None:
    tenant_id = _tenant()
    definition = conservative_preset()
    with Session(migrated_engine) as session, session.begin():
        store = ResolutionPolicyStore(session)
        model = store.materialize(tenant_id, definition, preset_kind="Conservative")
        policy_id = model.policy_id

    with Session(migrated_engine) as session:
        row = session.get(ResolutionPolicyModel, policy_id)
        assert row is not None
        assert row.tenant_id == tenant_id
        assert row.policy_name == "Conservative"
        assert row.policy_version == definition.policy_version
        assert row.preset_kind == "Conservative"
        assert row.status == "Active"


def test_materialize_is_idempotent_and_never_creates_a_duplicate_row(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant()
    definition = conservative_preset()
    with Session(migrated_engine) as session, session.begin():
        store = ResolutionPolicyStore(session)
        first = store.materialize(tenant_id, definition, preset_kind="Conservative")
        second = store.materialize(tenant_id, definition, preset_kind="Conservative")
        session.flush()
        assert first.policy_id == second.policy_id

    with Session(migrated_engine) as session:
        rows = session.scalars(
            select(ResolutionPolicyModel).where(
                ResolutionPolicyModel.tenant_id == tenant_id,
                ResolutionPolicyModel.policy_name == "Conservative",
                ResolutionPolicyModel.policy_version == definition.policy_version,
            )
        ).all()
        assert len(rows) == 1


def test_materialize_built_in_presets_creates_exactly_the_three_presets(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant()
    with Session(migrated_engine) as session, session.begin():
        store = ResolutionPolicyStore(session)
        models = store.materialize_built_in_presets(tenant_id)
        assert len(models) == len(BUILT_IN_PRESETS) == 3
        assert {m.policy_name for m in models} == {"Conservative", "Balanced", "Exploratory"}

    with Session(migrated_engine) as session:
        rows = session.scalars(
            select(ResolutionPolicyModel).where(ResolutionPolicyModel.tenant_id == tenant_id)
        ).all()
        assert len(rows) == 3


def test_two_tenants_materializing_the_same_preset_get_distinct_rows(
    migrated_engine: Engine,
) -> None:
    """No shared "platform" policy row: each tenant owns its own materialized
    copy, even for an identical built-in preset definition."""
    tenant_a = _tenant()
    tenant_b = _tenant()
    definition = conservative_preset()
    with Session(migrated_engine) as session, session.begin():
        store = ResolutionPolicyStore(session)
        model_a = store.materialize(tenant_a, definition, preset_kind="Conservative")
        model_b = store.materialize(tenant_b, definition, preset_kind="Conservative")
        policy_id_a, tenant_id_a = model_a.policy_id, model_a.tenant_id
        policy_id_b, tenant_id_b = model_b.policy_id, model_b.tenant_id

    assert policy_id_a != policy_id_b
    assert tenant_id_a != tenant_id_b


def test_get_by_id_is_tenant_scoped(migrated_engine: Engine) -> None:
    owner_tenant = _tenant()
    other_tenant = _tenant()
    definition = conservative_preset()
    with Session(migrated_engine) as session, session.begin():
        store = ResolutionPolicyStore(session)
        model = store.materialize(owner_tenant, definition, preset_kind="Conservative")
        policy_id = model.policy_id

    with Session(migrated_engine) as session:
        store = ResolutionPolicyStore(session)
        assert store.get_by_id(owner_tenant, policy_id) is not None
        assert store.get_by_id(other_tenant, policy_id) is None


def test_list_for_tenant_only_returns_that_tenants_policies(migrated_engine: Engine) -> None:
    tenant_a = _tenant()
    tenant_b = _tenant()
    with Session(migrated_engine) as session, session.begin():
        store = ResolutionPolicyStore(session)
        store.materialize_built_in_presets(tenant_a)
        store.materialize(tenant_b, conservative_preset(), preset_kind="Conservative")

    with Session(migrated_engine) as session:
        store = ResolutionPolicyStore(session)
        tenant_a_policies = store.list_for_tenant(tenant_a)
        tenant_b_policies = store.list_for_tenant(tenant_b)

    assert len(tenant_a_policies) == 3
    assert all(p.tenant_id == tenant_a for p in tenant_a_policies)
    assert len(tenant_b_policies) == 1
    assert all(p.tenant_id == tenant_b for p in tenant_b_policies)


def test_as_definition_round_trips_to_an_equal_policy_definition(migrated_engine: Engine) -> None:
    tenant_id = _tenant()
    definition = conservative_preset()
    with Session(migrated_engine) as session, session.begin():
        store = ResolutionPolicyStore(session)
        model = store.materialize(tenant_id, definition, preset_kind="Conservative")
        policy_id = model.policy_id

    with Session(migrated_engine) as session:
        store = ResolutionPolicyStore(session)
        row = session.get(ResolutionPolicyModel, policy_id)
        assert row is not None
        restored = store.as_definition(row)

    assert restored == definition
