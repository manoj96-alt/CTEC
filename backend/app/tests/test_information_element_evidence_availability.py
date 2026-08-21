"""Unit tests for `InformationElementEvidenceAvailabilityApplicationService`
(H4; CDD-023 §8-§17; H4 Evidence Availability Artifact Authorization).
Uses an `EvidenceProvider`-conforming test double -- no PostgreSQL
dependency: `FieldValueEvidenceRepositoryImpl`'s own query logic is
already proven against real Postgres elsewhere (CDD-022); re-proving it
here would duplicate existing coverage without adding evidence value.
"""

import inspect
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    InformationElementCoverageResult,
    SemanticCoverageEvaluationResult,
)
from app.domain.blueprint import Obligation
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingResolution

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TENANT_ID = "tenant-a"


def _resolution(*, source_field_id: UUID | None = None) -> SemanticMappingResolution:
    return SemanticMappingResolution(
        semantic_mapping_id=uuid4(),
        source_field_id=source_field_id if source_field_id is not None else uuid4(),
        source_object_id=uuid4(),
        source_system_id=uuid4(),
        information_element_requirement_id=uuid4(),
        created_by=uuid4(),
        created_on=NOW,
        modified_by=None,
        modified_on=None,
    )


def _mapped_element(
    *,
    obligation: Obligation = Obligation.REQUIRED,
    resolution: SemanticMappingResolution | None = None,
) -> InformationElementCoverageResult:
    resolved = resolution if resolution is not None else _resolution()
    return InformationElementCoverageResult(
        information_element_requirement_id=resolved.information_element_requirement_id,
        obligation=obligation,
        status=CoverageStatus.MAPPED,
        resolution=resolved,
    )


def _unmapped_element(
    *, obligation: Obligation = Obligation.REQUIRED
) -> InformationElementCoverageResult:
    return InformationElementCoverageResult(
        information_element_requirement_id=uuid4(),
        obligation=obligation,
        status=CoverageStatus.UNMAPPED,
        resolution=None,
    )


def _coverage_result(
    *, elements: tuple[InformationElementCoverageResult, ...], tenant_id: str = TENANT_ID
) -> SemanticCoverageEvaluationResult:
    return SemanticCoverageEvaluationResult(
        blueprint_id=uuid4(),
        blueprint_version_number=1,
        tenant_id=tenant_id,
        evaluated_at=NOW,
        information_element_results=elements,
    )


def _evidence(
    *, source_field_id: UUID, observed_representation: str, observed_at: datetime = NOW
) -> FieldValueEvidence:
    return FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference="100045",
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


# ---------------------------------------------------------------------------
# 1-6: three-state classification
# ---------------------------------------------------------------------------


def test_mapped_with_zero_evidence_rows_yields_no_evidence() -> None:
    element = _mapped_element()
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert len(result) == 1
    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.NO_EVIDENCE
    assert result[0].field_value_evidence_ids == ()


def test_mapped_with_one_empty_row_yields_evidence_empty() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    row = _evidence(source_field_id=source_field_id, observed_representation="")
    provider = _FakeEvidenceProvider({source_field_id: (row,)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_EMPTY
    assert result[0].field_value_evidence_ids == (row.field_value_evidence_id.value,)


def test_mapped_with_multiple_all_empty_rows_yields_evidence_empty() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    row_a = _evidence(source_field_id=source_field_id, observed_representation="", observed_at=NOW)
    row_b = _evidence(
        source_field_id=source_field_id,
        observed_representation="",
        observed_at=NOW + timedelta(days=1),
    )
    provider = _FakeEvidenceProvider({source_field_id: (row_a, row_b)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_EMPTY
    assert set(result[0].field_value_evidence_ids) == {
        row_a.field_value_evidence_id.value,
        row_b.field_value_evidence_id.value,
    }


def test_mapped_with_one_non_empty_row_yields_evidence_present() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    row = _evidence(source_field_id=source_field_id, observed_representation="Acme Taiwan Ltd")
    provider = _FakeEvidenceProvider({source_field_id: (row,)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    assert result[0].field_value_evidence_ids == (row.field_value_evidence_id.value,)


def test_mapped_with_mixed_empty_and_non_empty_rows_yields_evidence_present() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    empty_row = _evidence(
        source_field_id=source_field_id, observed_representation="", observed_at=NOW
    )
    present_row = _evidence(
        source_field_id=source_field_id,
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW + timedelta(days=1),
    )
    provider = _FakeEvidenceProvider({source_field_id: (empty_row, present_row)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    # Both IDs present -- never only the non-empty one.
    assert set(result[0].field_value_evidence_ids) == {
        empty_row.field_value_evidence_id.value,
        present_row.field_value_evidence_id.value,
    }


def test_whitespace_only_representation_yields_evidence_present() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    row = _evidence(source_field_id=source_field_id, observed_representation=" ")
    provider = _FakeEvidenceProvider({source_field_id: (row,)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_PRESENT


# ---------------------------------------------------------------------------
# 7-8: MAPPED / UNMAPPED firewall
# ---------------------------------------------------------------------------


def test_unmapped_element_produces_no_result() -> None:
    element = _unmapped_element()
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result == ()
    assert provider.requested_arguments == []


def test_mapped_element_produces_exactly_one_result() -> None:
    element = _mapped_element()
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert len(result) == 1


# ---------------------------------------------------------------------------
# 9-11: obligation passthrough
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.OPTIONAL, Obligation.CONDITIONAL]
)
def test_obligation_is_preserved_and_zero_evidence_always_yields_no_evidence(
    obligation: Obligation,
) -> None:
    element = _mapped_element(obligation=obligation)
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].obligation is obligation
    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.NO_EVIDENCE


def test_source_field_id_matches_the_embedded_resolution() -> None:
    source_field_id = uuid4()
    resolution = _resolution(source_field_id=source_field_id)
    element = _mapped_element(resolution=resolution)
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].source_field_id == source_field_id
    assert result[0].source_field_id == result[0].semantic_mapping_resolution.source_field_id
    assert result[0].semantic_mapping_resolution is resolution


# ---------------------------------------------------------------------------
# 12-15: provenance ordering, no selection, duplicates
# ---------------------------------------------------------------------------


def test_evidence_id_ordering_is_canonical_lexical_regardless_of_provider_return_order() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    row_a = _evidence(source_field_id=source_field_id, observed_representation="a", observed_at=NOW)
    row_b = _evidence(
        source_field_id=source_field_id,
        observed_representation="b",
        observed_at=NOW + timedelta(days=1),
    )
    expected_order = tuple(
        sorted([row_a.field_value_evidence_id.value, row_b.field_value_evidence_id.value], key=str)
    )
    # Deliberately return rows in reverse-ID order to prove the service re-sorts.
    reverse_rows = (
        (row_b, row_a)
        if expected_order[0] == row_a.field_value_evidence_id.value
        else (row_a, row_b)
    )
    provider = _FakeEvidenceProvider({source_field_id: reverse_rows})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].field_value_evidence_ids == expected_order


def test_ordering_is_unaffected_by_timestamps_representation_or_reference() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    row_a = FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference="100045",
        observed_representation="zzz",
        observed_at=NOW + timedelta(days=10),
        received_at=NOW + timedelta(days=10),
        evidence_reference="zzz-ref",
    )
    row_b = FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference="100046",
        observed_representation="aaa",
        observed_at=NOW,
        received_at=NOW,
        evidence_reference="aaa-ref",
    )
    expected_order = tuple(
        sorted([row_a.field_value_evidence_id.value, row_b.field_value_evidence_id.value], key=str)
    )
    provider = _FakeEvidenceProvider({source_field_id: (row_a, row_b)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].field_value_evidence_ids == expected_order


def test_duplicate_field_value_evidence_id_raises_validation_exception() -> None:
    source_field_id = uuid4()
    element = _mapped_element(resolution=_resolution(source_field_id=source_field_id))
    row = _evidence(source_field_id=source_field_id, observed_representation="Acme Taiwan Ltd")
    provider = _FakeEvidenceProvider({source_field_id: (row, row)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    with pytest.raises(ValidationException, match="duplicate"):
        service.evaluate(coverage_result=_coverage_result(elements=(element,)))


def test_wrong_tenant_error_propagates_unchanged() -> None:
    element = _mapped_element()
    provider = _FakeEvidenceProvider(
        error=ValidationException("Field Value Evidence tenant ownership mismatch")
    )
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    with pytest.raises(ValidationException, match="tenant ownership mismatch"):
        service.evaluate(coverage_result=_coverage_result(elements=(element,)))


# ---------------------------------------------------------------------------
# 16-17, 19a: evaluated_at
# ---------------------------------------------------------------------------


def test_evaluated_at_is_timezone_aware_utc() -> None:
    element = _mapped_element()
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element,)))

    assert result[0].evaluated_at.tzinfo is not None
    assert result[0].evaluated_at.utcoffset() == timedelta(0)


def test_two_separate_invocations_may_differ_only_in_evaluated_at() -> None:
    element = _mapped_element()
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)
    coverage_result = _coverage_result(elements=(element,))

    first = service.evaluate(coverage_result=coverage_result)
    second = service.evaluate(coverage_result=coverage_result)

    assert first[0].evidence_availability_status == second[0].evidence_availability_status
    assert first[0].field_value_evidence_ids == second[0].field_value_evidence_ids


def test_wrong_tenant_error_never_becomes_no_evidence() -> None:
    element = _mapped_element()
    provider = _FakeEvidenceProvider(error=ValidationException("tenant ownership mismatch"))
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    with pytest.raises(ValidationException):
        service.evaluate(coverage_result=_coverage_result(elements=(element,)))


def test_multiple_mapped_elements_share_the_identical_evaluated_at() -> None:
    element_a = _mapped_element()
    element_b = _mapped_element()
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element_a, element_b)))

    assert len(result) == 2
    assert result[0].evaluated_at == result[1].evaluated_at


# ---------------------------------------------------------------------------
# 19: cross-element isolation
# ---------------------------------------------------------------------------


def test_multiple_mapped_elements_produce_independently_isolated_results() -> None:
    source_field_id_a = uuid4()
    source_field_id_b = uuid4()
    element_a = _mapped_element(resolution=_resolution(source_field_id=source_field_id_a))
    element_b = _mapped_element(resolution=_resolution(source_field_id=source_field_id_b))
    row_a = _evidence(source_field_id=source_field_id_a, observed_representation="Acme Taiwan Ltd")
    provider = _FakeEvidenceProvider({source_field_id_a: (row_a,)})
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=(element_a, element_b)))

    by_source_field = {r.source_field_id: r for r in result}
    assert by_source_field[source_field_id_a].evidence_availability_status is (
        EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    )
    assert by_source_field[source_field_id_b].evidence_availability_status is (
        EvidenceAvailabilityStatus.NO_EVIDENCE
    )


# ---------------------------------------------------------------------------
# Deterministic outer ordering
# ---------------------------------------------------------------------------


def test_deterministic_outer_result_ordering() -> None:
    elements = tuple(_mapped_element() for _ in range(5))
    provider = _FakeEvidenceProvider()
    service = InformationElementEvidenceAvailabilityApplicationService(evidence_provider=provider)

    result = service.evaluate(coverage_result=_coverage_result(elements=elements))

    ids = [r.information_element_requirement_id for r in result]
    assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# 20: import hygiene / module surface
# ---------------------------------------------------------------------------


def test_service_exposes_no_method_beyond_evaluate() -> None:
    public_methods = {
        name
        for name, _ in inspect.getmembers(
            InformationElementEvidenceAvailabilityApplicationService, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert public_methods == {"evaluate"}


def _module_imported_names() -> set[str]:
    import ast

    import app.application.information_element_evidence_availability as module

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(alias.name for alias in node.names)
    return names


def test_module_imports_no_concrete_repository_orm_or_sqlalchemy() -> None:
    imported = _module_imported_names()
    assert not any("sqlalchemy" in name.lower() for name in imported)
    assert not any(name.endswith("ORM") for name in imported)
    assert "FieldValueEvidenceRepositoryImpl" not in imported


def test_module_imports_no_forbidden_capability() -> None:
    imported = _module_imported_names()
    forbidden = {
        "Blueprint",
        "SemanticMapping",
        "SemanticMappingResolutionApplicationService",
        "GapImpactContext",
        "RemediationAction",
        "SourceObservation",
    }
    assert imported.isdisjoint(forbidden)
    assert not any("app.integration" in name or "app.api" in name for name in imported)
    assert not any("fastapi" in name.lower() for name in imported)
