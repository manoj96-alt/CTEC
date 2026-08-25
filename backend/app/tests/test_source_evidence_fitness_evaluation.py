"""Unit tests for `SourceEvidenceFitnessEvaluationApplicationService` (Gate
T; CDD-031 §6-§14, §17-§19; Gate T Artifact Authorization §6, §9). Uses an
`EvidenceProvider`-conforming test double -- no PostgreSQL dependency:
`FieldValueEvidenceRepositoryImpl`'s own query logic is already proven
against real Postgres elsewhere (CDD-022); re-proving it here would
duplicate existing coverage without adding evidence value."""

import dataclasses
import inspect
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application import source_evidence_fitness_evaluation as fitness_module
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityResult,
)
from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    InformationElementEvidenceFitnessResult,
    SourceEvidenceFitnessEvaluationApplicationService,
)
from app.domain.blueprint import Obligation
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingResolution

NOW = datetime(2026, 1, 15, tzinfo=UTC)
TENANT_ID = "tenant-a"


def _resolution(*, source_field_id: UUID) -> SemanticMappingResolution:
    return SemanticMappingResolution(
        semantic_mapping_id=uuid4(),
        source_field_id=source_field_id,
        source_object_id=uuid4(),
        source_system_id=uuid4(),
        information_element_requirement_id=uuid4(),
        created_by=uuid4(),
        created_on=NOW,
        modified_by=None,
        modified_on=None,
    )


def _h4_result(
    *,
    information_element_requirement_id: UUID | None = None,
    source_field_id: UUID | None = None,
    evidence_availability_status: EvidenceAvailabilityStatus,
    field_value_evidence_ids: tuple[UUID, ...] = (),
) -> InformationElementEvidenceAvailabilityResult:
    resolved_source_field_id = source_field_id if source_field_id is not None else uuid4()
    resolved_requirement_id = (
        information_element_requirement_id
        if information_element_requirement_id is not None
        else uuid4()
    )
    return InformationElementEvidenceAvailabilityResult(
        information_element_requirement_id=resolved_requirement_id,
        obligation=Obligation.REQUIRED,
        semantic_mapping_resolution=_resolution(source_field_id=resolved_source_field_id),
        source_field_id=resolved_source_field_id,
        evidence_availability_status=evidence_availability_status,
        field_value_evidence_ids=field_value_evidence_ids,
        evaluated_at=NOW,
    )


def _evidence(
    *,
    source_field_id: UUID,
    source_record_reference: str = "100045",
    observed_representation: str,
    observed_at: datetime,
) -> FieldValueEvidence:
    return FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference=source_record_reference,
        observed_representation=observed_representation,
        observed_at=observed_at,
        received_at=NOW,
    )


class _FakeEvidenceProvider:
    def __init__(
        self,
        rows: dict[UUID, tuple[FieldValueEvidence, ...]] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.rows = rows or {}
        self.error = error
        self.requested_arguments: list[tuple[str, UUID]] = []

    def get_by_source_field(
        self, *, tenant_id: str, source_field_id: UUID
    ) -> tuple[FieldValueEvidence, ...]:
        self.requested_arguments.append((tenant_id, source_field_id))
        if self.error is not None:
            raise self.error
        return self.rows.get(source_field_id, ())


def _service(
    provider: _FakeEvidenceProvider | None = None,
) -> tuple[SourceEvidenceFitnessEvaluationApplicationService, _FakeEvidenceProvider]:
    fake = provider if provider is not None else _FakeEvidenceProvider()
    return SourceEvidenceFitnessEvaluationApplicationService(evidence_provider=fake), fake


# ---------------------------------------------------------------------------
# 1-4: eligibility / shape
# ---------------------------------------------------------------------------


def test_no_evidence_yields_none_and_does_not_call_provider() -> None:
    h4_result = _h4_result(evidence_availability_status=EvidenceAvailabilityStatus.NO_EVIDENCE)
    service, provider = _service()

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW
    )

    assert len(result) == 1
    assert result[0].fitness_status is None
    assert provider.requested_arguments == []


def test_evidence_empty_yields_none_and_does_not_call_provider() -> None:
    h4_result = _h4_result(evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_EMPTY)
    service, provider = _service()

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW
    )

    assert len(result) == 1
    assert result[0].fitness_status is None
    assert provider.requested_arguments == []


def test_evidence_present_yields_fit_stale_or_conflicting() -> None:
    source_field_id = uuid4()
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    row = _evidence(source_field_id=source_field_id, observed_representation="TW", observed_at=NOW)
    service, _ = _service(_FakeEvidenceProvider({source_field_id: (row,)}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW
    )

    assert result[0].fitness_status in (
        EvidenceFitnessStatus.FIT,
        EvidenceFitnessStatus.STALE,
        EvidenceFitnessStatus.CONFLICTING,
    )


def test_one_result_per_h4_result_received() -> None:
    h4_results = (
        _h4_result(evidence_availability_status=EvidenceAvailabilityStatus.NO_EVIDENCE),
        _h4_result(evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_EMPTY),
        _h4_result(evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT),
    )
    service, _ = _service()

    result = service.evaluate(
        evidence_availability_results=h4_results, tenant_id=TENANT_ID, as_of=NOW
    )

    assert len(result) == len(h4_results)


# ---------------------------------------------------------------------------
# 5-8: result contract shape
# ---------------------------------------------------------------------------


def test_source_field_id_is_present() -> None:
    source_field_id = uuid4()
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.NO_EVIDENCE,
    )
    service, _ = _service()

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW
    )

    assert result[0].source_field_id == source_field_id


def test_result_contract_contains_exactly_three_fields() -> None:
    field_names = {
        field.name for field in dataclasses.fields(InformationElementEvidenceFitnessResult)
    }
    assert field_names == {
        "information_element_requirement_id",
        "source_field_id",
        "fitness_status",
    }


def test_evidence_fitness_status_has_exactly_three_members() -> None:
    assert {member.value for member in EvidenceFitnessStatus} == {"FIT", "STALE", "CONFLICTING"}


# ---------------------------------------------------------------------------
# 9: determinism
# ---------------------------------------------------------------------------


def test_repeated_evaluation_with_identical_inputs_is_value_equal() -> None:
    source_field_id = uuid4()
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    row = _evidence(source_field_id=source_field_id, observed_representation="TW", observed_at=NOW)
    service, _ = _service(_FakeEvidenceProvider({source_field_id: (row,)}))

    first = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW
    )
    second = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW
    )

    assert first == second


def test_module_never_calls_datetime_now() -> None:
    source = inspect.getsource(fitness_module)
    assert "datetime.now(" not in source


# ---------------------------------------------------------------------------
# 10-16: freshness / conflict
# ---------------------------------------------------------------------------


def test_exactly_seven_days_old_remains_fit() -> None:
    source_field_id = uuid4()
    as_of = NOW
    row = _evidence(
        source_field_id=source_field_id,
        observed_representation="TW",
        observed_at=as_of - timedelta(days=7),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: (row,)}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.FIT


def test_older_than_seven_days_produces_stale() -> None:
    source_field_id = uuid4()
    as_of = NOW
    row = _evidence(
        source_field_id=source_field_id,
        observed_representation="TW",
        observed_at=as_of - timedelta(days=7, seconds=1),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: (row,)}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.STALE


def test_future_dated_evidence_produces_stale() -> None:
    source_field_id = uuid4()
    as_of = NOW
    row = _evidence(
        source_field_id=source_field_id,
        observed_representation="TW",
        observed_at=as_of + timedelta(days=1),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: (row,)}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.STALE


def test_identical_values_in_one_comparable_group_do_not_conflict() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(source_field_id=source_field_id, observed_representation="TW", observed_at=as_of),
        _evidence(
            source_field_id=source_field_id,
            observed_representation="TW",
            observed_at=as_of - timedelta(days=1),
        ),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.FIT


def test_differing_non_empty_values_in_one_comparable_group_produce_conflicting() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(source_field_id=source_field_id, observed_representation="TW", observed_at=as_of),
        _evidence(source_field_id=source_field_id, observed_representation="CN", observed_at=as_of),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.CONFLICTING


def test_case_and_whitespace_variants_are_treated_as_conflicting_not_normalized() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(source_field_id=source_field_id, observed_representation="TW", observed_at=as_of),
        _evidence(
            source_field_id=source_field_id, observed_representation="TW ", observed_at=as_of
        ),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.CONFLICTING


def test_different_values_in_different_source_record_reference_groups_do_not_conflict() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-a",
            observed_representation="TW",
            observed_at=as_of,
        ),
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-b",
            observed_representation="CN",
            observed_at=as_of,
        ),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.FIT


def test_all_empty_comparable_group_is_excluded_even_with_multiple_empty_rows() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-a",
            observed_representation="",
            observed_at=as_of,
        ),
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-a",
            observed_representation="",
            observed_at=as_of - timedelta(days=30),
        ),
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-b",
            observed_representation="TW",
            observed_at=as_of,
        ),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.FIT


# ---------------------------------------------------------------------------
# 17-21: T6 edge cases
# ---------------------------------------------------------------------------


def test_all_empty_group_plus_fresh_non_conflicting_group_yields_fit() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-a",
            observed_representation="",
            observed_at=as_of,
        ),
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-b",
            observed_representation="TW",
            observed_at=as_of,
        ),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.FIT


def test_empty_row_plus_two_differing_non_empty_rows_in_same_group_yields_conflicting() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(source_field_id=source_field_id, observed_representation="", observed_at=as_of),
        _evidence(source_field_id=source_field_id, observed_representation="TW", observed_at=as_of),
        _evidence(source_field_id=source_field_id, observed_representation="CN", observed_at=as_of),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.CONFLICTING


def test_future_dated_evidence_that_is_also_conflicting_yields_conflicting() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(
            source_field_id=source_field_id,
            observed_representation="TW",
            observed_at=as_of + timedelta(days=1),
        ),
        _evidence(source_field_id=source_field_id, observed_representation="CN", observed_at=as_of),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.CONFLICTING


def test_old_evidence_that_is_also_conflicting_yields_conflicting() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(
            source_field_id=source_field_id,
            observed_representation="TW",
            observed_at=as_of - timedelta(days=30),
        ),
        _evidence(
            source_field_id=source_field_id,
            observed_representation="CN",
            observed_at=as_of - timedelta(days=30),
        ),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.CONFLICTING


def test_one_stale_group_plus_another_conflicting_group_yields_conflicting() -> None:
    source_field_id = uuid4()
    as_of = NOW
    rows = (
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-a",
            observed_representation="TW",
            observed_at=as_of - timedelta(days=30),
        ),
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-b",
            observed_representation="TW",
            observed_at=as_of,
        ),
        _evidence(
            source_field_id=source_field_id,
            source_record_reference="record-b",
            observed_representation="CN",
            observed_at=as_of,
        ),
    )
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, _ = _service(_FakeEvidenceProvider({source_field_id: rows}))

    result = service.evaluate(
        evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=as_of
    )

    assert result[0].fitness_status is EvidenceFitnessStatus.CONFLICTING


# ---------------------------------------------------------------------------
# 28-29: failure semantics / tenant isolation
# ---------------------------------------------------------------------------


def test_repository_validation_exception_propagates_unchanged() -> None:
    source_field_id = uuid4()
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    provider = _FakeEvidenceProvider(error=ValidationException("tenant ownership mismatch"))
    service, _ = _service(provider)

    with pytest.raises(ValidationException, match="tenant ownership mismatch"):
        service.evaluate(evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW)


def test_tenant_id_and_source_field_id_are_passed_through_to_the_provider() -> None:
    source_field_id = uuid4()
    h4_result = _h4_result(
        source_field_id=source_field_id,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service, provider = _service()

    service.evaluate(evidence_availability_results=(h4_result,), tenant_id=TENANT_ID, as_of=NOW)

    assert provider.requested_arguments == [(TENANT_ID, source_field_id)]


# ---------------------------------------------------------------------------
# structural / import firewall
# ---------------------------------------------------------------------------


def test_service_exposes_no_method_beyond_evaluate() -> None:
    public_methods = [
        name
        for name in dir(SourceEvidenceFitnessEvaluationApplicationService)
        if not name.startswith("_")
    ]
    assert public_methods == ["evaluate"]


def _module_imported_names() -> set[str]:
    import ast

    tree = ast.parse(inspect.getsource(fitness_module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(alias.name for alias in node.names)
    return names


def test_module_does_not_import_h4s_own_evidence_provider_protocol() -> None:
    imported = _module_imported_names()
    assert "EvidenceProvider" not in imported


def test_module_imports_no_concrete_repository_orm_or_sqlalchemy() -> None:
    imported = _module_imported_names()
    assert not any("sqlalchemy" in name.lower() for name in imported)
    assert not any(name.endswith("ORM") for name in imported)
    assert not any("Repository" in name for name in imported)
    assert not any(name == "Session" or name.endswith(".Session") for name in imported)
