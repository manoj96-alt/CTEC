"""Explicit, idempotent, demo-only seeder for the CDD-022 deterministic
Field-Value Evidence acceptance demonstration (CDD-022 §20, §21;
Field-Value Evidence Artifact Authorization §11).

Never invoked by normal production bootstrap: `app.main.lifespan` only ever
builds the dependency Container -- nothing there, or anywhere else on the
request path, calls this module. It has its own, separate, manually-run
CLI entrypoint (see `__main__` below) and must be invoked deliberately --
following `demo_semantic_mapping_seeder.py`'s exact precedent.

Refuses to seed any tenant other than the labeled demo tenant
(`BOOTSTRAP_DEMO_TENANT_ID`). Resolves the existing, unmodified H3 physical
source identity (`H3 Demo ERP` / `LFA1` / `LFA1-NAME1`) by calling the
existing, unmodified `DemoSemanticMappingSeeder(session).seed()` first --
never creating a `SourceSystem`/`SourceObject`/`SourceField`/`SemanticMapping`
row of its own. Constructs the one deterministic `FieldValueEvidence` fact
CDD-022 §21 requires (`source_record_reference = "100045"`,
`observed_representation = "Acme Taiwan Ltd"`) exclusively through the
domain-owned `FieldValueEvidence.new(...)` construction mechanism -- this
module contains no identity-derivation logic of its own (no `_stable_id`,
no `uuid5`, no `BOOTSTRAP_SEED_NAMESPACE` reference).

Idempotent: `FieldValueEvidenceRepositoryImpl.create_or_get_existing(...)`
returns the existing fact unchanged, preserving its original `received_at`,
on every re-run against an already-seeded database.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID, SEED_TIMESTAMP
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.demo_semantic_mapping_seeder import (
    DemoSemanticMappingSeeder,
    DemoTenantRequiredError,
)
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)

SOURCE_RECORD_REFERENCE = "100045"
OBSERVED_REPRESENTATION = "Acme Taiwan Ltd"
OBSERVED_AT: datetime = SEED_TIMESTAMP
RECEIVED_AT: datetime = SEED_TIMESTAMP


@dataclass(frozen=True, slots=True)
class DemoFieldValueEvidenceSeedSummary:
    field_value_evidence_id: UUID
    source_field_id: UUID
    source_record_reference: str
    observed_representation: str


class DemoFieldValueEvidenceSeeder:
    """Deterministically persists the CDD-022 demonstration evidence fact.
    Idempotent: safe to call repeatedly."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def seed(self, tenant_id: str = BOOTSTRAP_DEMO_TENANT_ID) -> DemoFieldValueEvidenceSeedSummary:
        if tenant_id != BOOTSTRAP_DEMO_TENANT_ID:
            raise DemoTenantRequiredError(
                f"The demo field-value evidence seeder refuses to seed tenant {tenant_id!r}; "
                f"it only ever seeds the labeled demo tenant {BOOTSTRAP_DEMO_TENANT_ID!r}."
            )

        mapping_summary = DemoSemanticMappingSeeder(self._session).seed(tenant_id)
        self._session.flush()

        evidence = FieldValueEvidence.new(
            source_field_id=Identifier(mapping_summary.source_field_id),
            source_record_reference=SOURCE_RECORD_REFERENCE,
            observed_representation=OBSERVED_REPRESENTATION,
            observed_at=OBSERVED_AT,
            received_at=RECEIVED_AT,
        )
        persisted = FieldValueEvidenceRepositoryImpl(self._session).create_or_get_existing(evidence)
        self._session.flush()

        return DemoFieldValueEvidenceSeedSummary(
            field_value_evidence_id=persisted.field_value_evidence_id.value,
            source_field_id=persisted.source_field_id.value,
            source_record_reference=persisted.source_record_reference,
            observed_representation=persisted.observed_representation,
        )


if __name__ == "__main__":
    from app.core.config import get_settings
    from app.infrastructure.persistence.database import create_database_engine
    from app.infrastructure.persistence.session import create_session_factory

    settings = get_settings()
    engine = create_database_engine(settings)
    sessions = create_session_factory(engine)
    with sessions.begin() as cli_session:
        result = DemoFieldValueEvidenceSeeder(cli_session).seed()
    print(result)
