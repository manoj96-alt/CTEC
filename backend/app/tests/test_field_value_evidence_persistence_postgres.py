"""Postgres-backed persistence tests for `FieldValueEvidence` (CDD-022 §13,
§15, §18, §19, §22-§25; Field-Value Evidence Artifact Authorization). Proves
the real migration-created table, the idempotent `create_or_get_existing`
replay guarantee, and tenant-scoped retrieval's real join through
`source_fields.source_object_id -> source_objects.tenant_id` -- all against
a real PostgreSQL database, composing the real, unmodified
`SourceFieldRepositoryImpl`/`SourceObjectRepositoryImpl` fixtures.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.tests.test_source_field_persistence_postgres import _seed_source_object, _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_field(session: Session, *, tenant_id: str, field_label: str = "LFA1-NAME1") -> UUID:
    object_id = _seed_source_object(session, tenant_id=tenant_id)
    field = _source_field(source_object_id=object_id, field_label=field_label)
    SourceFieldRepositoryImpl(session).create(field)
    session.flush()
    return field.source_field_id.value


def _evidence(
    *,
    source_field_id: UUID,
    source_record_reference: str = "100045",
    observed_representation: str = "Acme Taiwan Ltd",
    observed_at: datetime = NOW,
    received_at: datetime = NOW,
    evidence_reference: str | None = None,
) -> FieldValueEvidence:
    return FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference=source_record_reference,
        observed_representation=observed_representation,
        observed_at=observed_at,
        received_at=received_at,
        evidence_reference=evidence_reference,
    )


def test_migration_creates_the_field_value_evidence_table(migrated_engine: Engine) -> None:
    """Proves the table and its expected columns exist, without assuming
    the table is empty -- `migrated_engine` is session-scoped and shared
    across the whole suite, so other tests may have already inserted rows
    by the time this test runs."""
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        columns = set(
            session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'field_value_evidence'"
                )
            )
            .scalars()
            .all()
        )
    assert columns == {
        "field_value_evidence_id",
        "source_field_id",
        "source_record_reference",
        "observed_representation",
        "observed_at",
        "received_at",
        "evidence_reference",
    }


def test_first_create_persists_one_row(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        field_id = _seed_field(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=field_id)
        persisted = repository.create_or_get_existing(evidence)
        session.commit()

        row = session.get(FieldValueEvidenceORM, evidence.field_value_evidence_id.value)
    assert row is not None
    assert persisted.field_value_evidence_id == evidence.field_value_evidence_id


def test_retrieve_by_id(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        field_id = _seed_field(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=field_id)
        repository.create_or_get_existing(evidence)
        session.commit()

        loaded = repository.get_by_id(evidence.field_value_evidence_id.value)

    assert loaded is not None
    assert loaded.observed_representation == "Acme Taiwan Ltd"
    assert loaded.source_record_reference == "100045"


def test_get_by_id_returns_none_for_a_nonexistent_evidence_row(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        repository = FieldValueEvidenceRepositoryImpl(session)
        assert repository.get_by_id(uuid4()) is None


def test_invalid_source_field_reference_is_rejected_at_the_database_layer(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=uuid4())
        with pytest.raises(IntegrityError):
            repository.create_or_get_existing(evidence)
        session.rollback()


def test_tenant_and_source_field_retrieval_returns_the_persisted_fact(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=field_id)
        repository.create_or_get_existing(evidence)
        session.commit()

        results = repository.get_by_source_field(tenant_id=tenant_id, source_field_id=field_id)

    assert len(results) == 1
    assert results[0].field_value_evidence_id == evidence.field_value_evidence_id


def test_zero_evidence_returns_an_empty_tuple(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        results = repository.get_by_source_field(tenant_id=tenant_id, source_field_id=field_id)

    assert results == ()


def test_multiple_observations_coexist(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        first = _evidence(source_field_id=field_id, observed_at=NOW)
        second = _evidence(source_field_id=field_id, observed_at=NOW + timedelta(days=1))
        repository.create_or_get_existing(first)
        repository.create_or_get_existing(second)
        session.commit()

        results = repository.get_by_source_field(tenant_id=tenant_id, source_field_id=field_id)

    assert {r.field_value_evidence_id for r in results} == {
        first.field_value_evidence_id,
        second.field_value_evidence_id,
    }


def test_prior_observation_is_not_overwritten_by_a_later_distinct_one(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        first = _evidence(
            source_field_id=field_id, observed_at=NOW, observed_representation="Acme Taiwan Ltd"
        )
        repository.create_or_get_existing(first)
        session.commit()

        second = _evidence(
            source_field_id=field_id,
            observed_at=NOW + timedelta(days=1),
            observed_representation="Acme Taiwan Limited",
        )
        repository.create_or_get_existing(second)
        session.commit()

        loaded_first = repository.get_by_id(first.field_value_evidence_id.value)

    assert loaded_first is not None
    assert loaded_first.observed_representation == "Acme Taiwan Ltd"


def test_empty_evidence_is_distinguishable_from_no_evidence(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        empty = _evidence(source_field_id=field_id, observed_representation="")
        repository.create_or_get_existing(empty)
        session.commit()

        loaded = repository.get_by_id(empty.field_value_evidence_id.value)
        results = repository.get_by_source_field(tenant_id=tenant_id, source_field_id=field_id)

    assert loaded is not None
    assert loaded.observed_representation == ""
    assert len(results) == 1


def test_evidence_reference_is_nullable(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        field_id = _seed_field(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=field_id, evidence_reference=None)
        repository.create_or_get_existing(evidence)
        session.commit()

        loaded = repository.get_by_id(evidence.field_value_evidence_id.value)

    assert loaded is not None
    assert loaded.evidence_reference is None


def test_correct_tenant_retrieval_succeeds(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=field_id)
        repository.create_or_get_existing(evidence)
        session.commit()

        results = repository.get_by_source_field(tenant_id=tenant_id, source_field_id=field_id)

    assert len(results) == 1


def test_wrong_tenant_retrieval_fails_explicitly(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_a = f"tenant-a-{uuid4()}"
        tenant_b = f"tenant-b-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_a)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=field_id)
        repository.create_or_get_existing(evidence)
        session.commit()

        with pytest.raises(ValidationException, match="tenant ownership mismatch"):
            repository.get_by_source_field(tenant_id=tenant_b, source_field_id=field_id)


def test_no_cross_tenant_leakage_when_two_tenants_hold_equivalent_facts(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_a = f"tenant-a-{uuid4()}"
        tenant_b = f"tenant-b-{uuid4()}"
        field_a = _seed_field(session, tenant_id=tenant_a)
        field_b = _seed_field(session, tenant_id=tenant_b)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        repository.create_or_get_existing(_evidence(source_field_id=field_a))
        repository.create_or_get_existing(_evidence(source_field_id=field_b))
        session.commit()

        results_a = repository.get_by_source_field(tenant_id=tenant_a, source_field_id=field_a)
        results_b = repository.get_by_source_field(tenant_id=tenant_b, source_field_id=field_b)

    assert len(results_a) == 1
    assert len(results_b) == 1
    assert results_a[0].field_value_evidence_id != results_b[0].field_value_evidence_id


def test_identical_replay_row_count_remains_one(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        evidence = _evidence(source_field_id=field_id)
        repository.create_or_get_existing(evidence)
        session.commit()

        replay = _evidence(source_field_id=field_id)
        repository.create_or_get_existing(replay)
        session.commit()

        results = repository.get_by_source_field(tenant_id=tenant_id, source_field_id=field_id)

    assert len(results) == 1


def test_original_received_at_survives_replay(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        field_id = _seed_field(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        original = _evidence(source_field_id=field_id, received_at=NOW)
        repository.create_or_get_existing(original)
        session.commit()

        replay = _evidence(source_field_id=field_id, received_at=NOW + timedelta(days=5))
        result = repository.create_or_get_existing(replay)
        session.commit()

        loaded = repository.get_by_id(original.field_value_evidence_id.value)

    assert loaded is not None
    assert loaded.received_at == NOW
    assert result.received_at == NOW


def test_evidence_reference_only_replay_does_not_mutate_or_create(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        field_id = _seed_field(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        original = _evidence(source_field_id=field_id, evidence_reference=None)
        repository.create_or_get_existing(original)
        session.commit()

        replay = _evidence(source_field_id=field_id, evidence_reference="batch-99")
        result = repository.create_or_get_existing(replay)
        session.commit()

        loaded = repository.get_by_id(original.field_value_evidence_id.value)

    assert loaded is not None
    assert loaded.evidence_reference is None
    assert result.evidence_reference is None


def test_identity_conflict_fails_explicitly(migrated_engine: Engine) -> None:
    """Only reachable via corrupted persisted data: raw-inserts a row whose
    stored semantic fields disagree with what its own ID (correctly derived
    from a *different* observed_representation) would require, then proves
    `create_or_get_existing` detects and rejects the conflict rather than
    silently returning the mismatched row. The rejection surfaces from
    `FieldValueEvidence.__post_init__`'s own rehydration-verification (run
    unconditionally by `get_by_id`, which `create_or_get_existing` calls
    first to check for an existing row) -- an earlier, stricter catch than
    the repository's own semantic-field comparison, which this scenario
    never reaches."""
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        field_id = _seed_field(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        canonical = _evidence(source_field_id=field_id, observed_representation="Acme Taiwan Ltd")
        session.add(
            FieldValueEvidenceORM(
                field_value_evidence_id=canonical.field_value_evidence_id.value,
                source_field_id=field_id,
                source_record_reference=canonical.source_record_reference,
                observed_representation="Corrupted Value",
                observed_at=canonical.observed_at,
                received_at=canonical.received_at,
            )
        )
        session.commit()

        repository = FieldValueEvidenceRepositoryImpl(session)
        with pytest.raises(ValidationException, match="inconsistent with its own governed"):
            repository.create_or_get_existing(canonical)
