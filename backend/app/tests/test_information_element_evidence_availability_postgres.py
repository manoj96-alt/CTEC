"""Postgres-backed acceptance evidence for H4 (CDD-023 §8-§17, §26-§27; H4
Evidence Availability Artifact Authorization). Composes the real,
unmodified `SemanticCoverageEvaluationApplicationService` (for a real
Gate I result) and the real, unmodified `FieldValueEvidenceRepositoryImpl`
into the new `InformationElementEvidenceAvailabilityApplicationService`,
proving the H3/CDD-022 deterministic demonstration ("Supplier Legal Name"
EVIDENCE_PRESENT, "Risk Event Severity" no H4 result), tenant isolation,
persisted multiplicity, and the absence of any H4 persistence side effect
against real PostgreSQL.

The duplicate-`field_value_evidence_id` invariant (CDD-023 §11.6) is
proven exclusively at the unit level
(`test_information_element_evidence_availability.py::
test_duplicate_field_value_evidence_id_raises_validation_exception`), not
here: `field_value_evidence_id` is the table's primary key
(`0016_field_value_evidence.py`), so two persisted rows sharing that value
can never coexist in real PostgreSQL -- the scenario is structurally
unconstructible against a real database, unlike CDD-022's own
identity-*content*-conflict precedent (a single row whose stored fields
disagree with its own ID, not two rows sharing one ID).
"""

import dataclasses
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID, SEED_TIMESTAMP
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
    DemoFieldValueEvidenceSeedSummary,
)
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)


def _seed(factory: "sessionmaker[Session]") -> DemoFieldValueEvidenceSeedSummary:
    with factory() as session:
        summary = DemoFieldValueEvidenceSeeder(session).seed()
        session.commit()
    return summary


def _coverage_service(session: Session) -> SemanticCoverageEvaluationApplicationService:
    return SemanticCoverageEvaluationApplicationService(
        blueprint_service=BlueprintApplicationService(repository=BlueprintRepositoryImpl(session)),
        resolver=SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        ),
    )


def _h4_service(session: Session) -> InformationElementEvidenceAvailabilityApplicationService:
    return InformationElementEvidenceAvailabilityApplicationService(
        evidence_provider=FieldValueEvidenceRepositoryImpl(session)
    )


def _field_value_evidence_row_count(session: Session) -> int:
    return len(session.execute(select(FieldValueEvidenceORM)).all())


def test_h3_acceptance_supplier_legal_name_evidence_present(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        result = _h4_service(session).evaluate(coverage_result=coverage_result)

    assert len(result) == 1
    supplier_legal_name = result[0]
    assert supplier_legal_name.evidence_availability_status is (
        EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    )
    assert supplier_legal_name.field_value_evidence_ids == (summary.field_value_evidence_id,)
    assert supplier_legal_name.source_field_id == summary.source_field_id


def test_risk_event_severity_unmapped_produces_no_h4_result(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        result = _h4_service(session).evaluate(coverage_result=coverage_result)

    # Only "Supplier Legal Name" (MAPPED) produces a result; "Risk Event
    # Severity" (UNMAPPED in the real H3 fixture) does not appear at all --
    # never as a NO_EVIDENCE result.
    assert len(result) == 1
    assert result[0].source_field_id == summary.source_field_id


def test_wrong_tenant_raises_explicitly_never_no_evidence(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    other_tenant_id = f"h4-isolation-tenant-{uuid4()}"

    with factory() as session:
        real_coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        # The real Gate I result is correctly tenant-scoped; simulate a
        # caller-side tenant mismatch (the only way this can arise, since
        # H4 never re-derives tenant_id itself) by substituting a
        # different tenant_id on an otherwise-real coverage_result, then
        # running it through the real H4 service end to end.
        wrong_tenant_coverage_result = dataclasses.replace(
            real_coverage_result, tenant_id=other_tenant_id
        )
        with pytest.raises(ValidationException, match="tenant ownership mismatch"):
            _h4_service(session).evaluate(coverage_result=wrong_tenant_coverage_result)


def test_persisted_multiplicity_full_provenance(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        second = FieldValueEvidence.new(
            source_field_id=Identifier(summary.source_field_id),
            source_record_reference="100045",
            observed_representation="Acme Taiwan Limited",
            observed_at=SEED_TIMESTAMP + timedelta(days=1),
            received_at=SEED_TIMESTAMP + timedelta(days=1),
        )
        FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(second)
        session.commit()

        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        result = _h4_service(session).evaluate(coverage_result=coverage_result)

    assert len(result) == 1
    assert len(result[0].field_value_evidence_ids) == 2
    assert summary.field_value_evidence_id in result[0].field_value_evidence_ids
    assert second.field_value_evidence_id.value in result[0].field_value_evidence_ids
    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_PRESENT


def test_repeated_evaluation_is_deterministic(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        service = _h4_service(session)
        first = service.evaluate(coverage_result=coverage_result)
        second = service.evaluate(coverage_result=coverage_result)

    assert first[0].evidence_availability_status == second[0].evidence_availability_status
    assert first[0].field_value_evidence_ids == second[0].field_value_evidence_ids
    assert first[0].source_field_id == second[0].source_field_id


def test_no_h4_persistence_side_effect(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        before = _field_value_evidence_row_count(session)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        _h4_service(session).evaluate(coverage_result=coverage_result)
        session.commit()

    with factory() as session:
        after = _field_value_evidence_row_count(session)

    assert after == before
