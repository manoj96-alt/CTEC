"""Unit-level proof of
EntityResolutionStewardApiService._source_representations()'s defensive
guard against missing source provenance, using an isolated in-memory
SQLite database rather than the shared PostgreSQL integration database.

SQLite does not enforce foreign keys unless a session explicitly opts in
(PRAGMA foreign_keys = ON, never done here), so a SourceObject row can be
inserted referencing a SourceSystem id that was never created. This lets
the test construct the "missing SourceSystem" state directly and safely:
the whole database is created fresh and discarded when the test function
returns, with zero risk to -- and zero interaction with -- any shared
fixture (in particular, migrated_engine, which is session-scoped and
shared across the whole PostgreSQL test session).

The real PostgreSQL composite foreign key
(fk_source_objects_tenant_source_system) makes this state structurally
unreachable during real operation -- see
test_source_system_referenced_by_a_source_object_cannot_be_deleted in
test_entity_resolution_steward_api_postgres.py, which proves the FK
actually rejects deleting a referenced source system. Between the two
tests: the schema-level protection is proven against real PostgreSQL, and
the defensive application-code guard for the (should-be-impossible) case
where that protection is somehow bypassed is proven here, in isolation.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.application.entity_resolution_steward_api import (
    EntityResolutionStewardApiService,
    IncompleteSourceProvenanceError,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _isolated_engine() -> Engine:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _seed_source_object_without_its_system(
    session: Session, *, tenant_id: str
) -> tuple[UUID, UUID]:
    """Inserts a SourceObject whose source_system_id has no corresponding
    SourceSystem row -- allowed here only because this isolated SQLite
    database never enforces that foreign key."""
    system_id = uuid4()
    source_id = uuid4()
    session.add(
        SourceObject(
            source_object_id=source_id,
            tenant_id=tenant_id,
            source_object_name=f"obj-{uuid4()}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=system_id,
        )
    )
    session.flush()
    return source_id, system_id


def test_missing_source_system_fails_explicitly_not_silently() -> None:
    engine = _isolated_engine()
    tenant_id = f"tenant-{uuid4()}"
    with Session(engine) as session, session.begin():
        source_id, system_id = _seed_source_object_without_its_system(session, tenant_id=tenant_id)

    with Session(engine) as session:
        with pytest.raises(IncompleteSourceProvenanceError) as excinfo:
            EntityResolutionStewardApiService._source_representations(
                session, tenant_id, (source_id,)
            )
        # Fails explicitly, and the message identifies the gap without
        # disclosing anything beyond the tenant id and the missing id itself.
        assert str(system_id) in str(excinfo.value)
        assert tenant_id in str(excinfo.value)


def test_missing_source_object_fails_explicitly_not_silently_at_the_service_layer() -> None:
    """Complements test_missing_source_object_fails_explicitly_not_silently
    in the PostgreSQL suite (which proves it through the full get_case()
    read path); this proves the same guard directly at the
    _source_representations() seam with no seeded data at all."""
    engine = _isolated_engine()
    tenant_id = f"tenant-{uuid4()}"
    with Session(engine) as session:
        with pytest.raises(IncompleteSourceProvenanceError):
            EntityResolutionStewardApiService._source_representations(
                session, tenant_id, (uuid4(),)
            )


def test_present_source_object_and_system_resolve_without_error() -> None:
    """Sanity check: the guard only fires when provenance is actually
    missing -- a fully-linked SourceObject/SourceSystem pair resolves
    normally through the same seam."""
    engine = _isolated_engine()
    tenant_id = f"tenant-{uuid4()}"
    system_id = uuid4()
    source_id = uuid4()
    with Session(engine) as session, session.begin():
        session.add(
            SourceSystem(
                source_system_id=system_id,
                tenant_id=tenant_id,
                source_system_name=f"sys-{uuid4()}",
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
            )
        )
        session.add(
            SourceObject(
                source_object_id=source_id,
                tenant_id=tenant_id,
                source_object_name=f"obj-{uuid4()}",
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                source_system_id=system_id,
            )
        )

    with Session(engine) as session:
        result = EntityResolutionStewardApiService._source_representations(
            session, tenant_id, (source_id,)
        )
    assert len(result) == 1
    assert result[0].source_object_id == source_id
    assert result[0].source_system_id == system_id
