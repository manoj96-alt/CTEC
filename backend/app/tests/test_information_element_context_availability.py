"""Unit tests for `InformationElementContextAvailabilityApplicationService`
(Gate N; CDD-024 §8-§15; Context Availability Composition Artifact
Authorization). Both inputs are hand-built, already-in-memory result
objects -- no PostgreSQL dependency and no fake I/O provider, since the
service under test performs no I/O of any kind.
"""

import dataclasses
import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityApplicationService,
    InformationElementContextAvailabilityResult,
)
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityResult,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    InformationElementCoverageResult,
    SemanticCoverageEvaluationResult,
)
from app.domain.blueprint import Obligation
from app.domain.shared.exceptions import ValidationException
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


def _h4_result(
    *,
    element: InformationElementCoverageResult,
    evidence_availability_status: EvidenceAvailabilityStatus = EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    source_field_id: UUID | None = None,
) -> InformationElementEvidenceAvailabilityResult:
    assert element.resolution is not None
    return InformationElementEvidenceAvailabilityResult(
        information_element_requirement_id=element.information_element_requirement_id,
        obligation=element.obligation,
        semantic_mapping_resolution=element.resolution,
        source_field_id=(
            source_field_id if source_field_id is not None else element.resolution.source_field_id
        ),
        evidence_availability_status=evidence_availability_status,
        field_value_evidence_ids=(uuid4(),),
        evaluated_at=NOW,
    )


# ---------------------------------------------------------------------------
# 1-4: composition semantics
# ---------------------------------------------------------------------------


def test_unmapped_with_no_h4_result_composes_to_none() -> None:
    element = _unmapped_element()
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=()
    )

    assert len(result) == 1
    assert result[0].coverage_status is CoverageStatus.UNMAPPED
    assert result[0].evidence_availability_status is None


def test_mapped_with_no_evidence_composes_passthrough() -> None:
    element = _mapped_element()
    h4 = _h4_result(
        element=element, evidence_availability_status=EvidenceAvailabilityStatus.NO_EVIDENCE
    )
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=(h4,)
    )

    assert result[0].coverage_status is CoverageStatus.MAPPED
    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.NO_EVIDENCE


def test_mapped_with_evidence_empty_composes_passthrough() -> None:
    element = _mapped_element()
    h4 = _h4_result(
        element=element, evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_EMPTY
    )
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=(h4,)
    )

    assert result[0].coverage_status is CoverageStatus.MAPPED
    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_EMPTY


def test_mapped_with_evidence_present_composes_passthrough() -> None:
    element = _mapped_element()
    h4 = _h4_result(
        element=element, evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    )
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=(h4,)
    )

    assert result[0].coverage_status is CoverageStatus.MAPPED
    assert result[0].evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_PRESENT


# ---------------------------------------------------------------------------
# 5-9: composition-integrity validation
# ---------------------------------------------------------------------------


def test_mapped_with_zero_h4_matches_raises() -> None:
    element = _mapped_element()
    service = InformationElementContextAvailabilityApplicationService()

    with pytest.raises(ValidationException, match="no corresponding H4 result"):
        service.compose(
            coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=()
        )


def test_mapped_with_duplicate_h4_matches_raises() -> None:
    element = _mapped_element()
    h4_a = _h4_result(element=element)
    h4_b = _h4_result(element=element)
    service = InformationElementContextAvailabilityApplicationService()

    with pytest.raises(ValidationException, match="more than one H4 result"):
        service.compose(
            coverage_result=_coverage_result(elements=(element,)),
            evidence_availability_results=(h4_a, h4_b),
        )


def test_unmapped_with_h4_result_present_raises() -> None:
    unmapped = _unmapped_element()
    mapped_for_resolution = _mapped_element()
    stray_h4 = InformationElementEvidenceAvailabilityResult(
        information_element_requirement_id=unmapped.information_element_requirement_id,
        obligation=unmapped.obligation,
        semantic_mapping_resolution=mapped_for_resolution.resolution,  # type: ignore[arg-type]
        source_field_id=mapped_for_resolution.resolution.source_field_id,  # type: ignore[union-attr]
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
        field_value_evidence_ids=(uuid4(),),
        evaluated_at=NOW,
    )
    service = InformationElementContextAvailabilityApplicationService()

    with pytest.raises(ValidationException, match="has an H4 result present"):
        service.compose(
            coverage_result=_coverage_result(elements=(unmapped,)),
            evidence_availability_results=(stray_h4,),
        )


def test_orphan_h4_result_raises() -> None:
    element = _mapped_element()
    orphan_element = _mapped_element()
    orphan_h4 = _h4_result(element=orphan_element)
    service = InformationElementContextAvailabilityApplicationService()

    with pytest.raises(ValidationException, match="not present in the supplied coverage_result"):
        service.compose(
            coverage_result=_coverage_result(elements=(element,)),
            evidence_availability_results=(orphan_h4,),
        )


def test_conflicting_provenance_raises() -> None:
    element = _mapped_element()
    h4 = _h4_result(element=element, source_field_id=uuid4())
    service = InformationElementContextAvailabilityApplicationService()

    with pytest.raises(ValidationException, match="provenance disagrees"):
        service.compose(
            coverage_result=_coverage_result(elements=(element,)),
            evidence_availability_results=(h4,),
        )


# ---------------------------------------------------------------------------
# 10-11: obligation and coverage_status passthrough
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.OPTIONAL, Obligation.CONDITIONAL]
)
def test_obligation_is_preserved_under_mapped(obligation: Obligation) -> None:
    element = _mapped_element(obligation=obligation)
    h4 = _h4_result(element=element)
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=(h4,)
    )

    assert result[0].obligation is obligation


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.OPTIONAL, Obligation.CONDITIONAL]
)
def test_obligation_is_preserved_under_unmapped(obligation: Obligation) -> None:
    element = _unmapped_element(obligation=obligation)
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=()
    )

    assert result[0].obligation is obligation


def test_coverage_status_is_always_the_source_elements_own_status() -> None:
    mapped = _mapped_element()
    h4 = _h4_result(element=mapped)
    unmapped = _unmapped_element()
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(mapped, unmapped)),
        evidence_availability_results=(h4,),
    )

    by_id = {r.information_element_requirement_id: r for r in result}
    assert by_id[mapped.information_element_requirement_id].coverage_status is CoverageStatus.MAPPED
    assert (
        by_id[unmapped.information_element_requirement_id].coverage_status
        is CoverageStatus.UNMAPPED
    )


# ---------------------------------------------------------------------------
# 12: cross-element isolation
# ---------------------------------------------------------------------------


def test_multiple_elements_compose_independently_isolated_results() -> None:
    mapped_present = _mapped_element()
    h4_present = _h4_result(
        element=mapped_present,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    mapped_no_evidence = _mapped_element()
    h4_no_evidence = _h4_result(
        element=mapped_no_evidence,
        evidence_availability_status=EvidenceAvailabilityStatus.NO_EVIDENCE,
    )
    unmapped = _unmapped_element()
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(mapped_present, mapped_no_evidence, unmapped)),
        evidence_availability_results=(h4_present, h4_no_evidence),
    )

    by_id = {r.information_element_requirement_id: r for r in result}
    assert (
        by_id[mapped_present.information_element_requirement_id].evidence_availability_status
        is EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    )
    assert (
        by_id[mapped_no_evidence.information_element_requirement_id].evidence_availability_status
        is EvidenceAvailabilityStatus.NO_EVIDENCE
    )
    assert by_id[unmapped.information_element_requirement_id].evidence_availability_status is None


# ---------------------------------------------------------------------------
# 13-14: determinism
# ---------------------------------------------------------------------------


def test_output_is_sorted_ascending_regardless_of_input_order() -> None:
    elements = tuple(_mapped_element() for _ in range(5))
    h4_results = tuple(_h4_result(element=e) for e in reversed(elements))
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=tuple(reversed(elements))),
        evidence_availability_results=h4_results,
    )

    ids = [r.information_element_requirement_id for r in result]
    assert ids == sorted(ids)


def test_repeated_composition_of_unchanged_input_is_identical() -> None:
    element = _mapped_element()
    h4 = _h4_result(element=element)
    service = InformationElementContextAvailabilityApplicationService()
    coverage_result = _coverage_result(elements=(element,))

    first = service.compose(coverage_result=coverage_result, evidence_availability_results=(h4,))
    second = service.compose(coverage_result=coverage_result, evidence_availability_results=(h4,))

    assert first == second


# ---------------------------------------------------------------------------
# 15: zero-dependency construction
# ---------------------------------------------------------------------------


def test_service_requires_no_constructor_arguments() -> None:
    service = InformationElementContextAvailabilityApplicationService()
    assert service is not None


def test_service_declares_no_init() -> None:
    assert "__init__" not in InformationElementContextAvailabilityApplicationService.__dict__


# ---------------------------------------------------------------------------
# 16: import hygiene
# ---------------------------------------------------------------------------


def _module_imported_names() -> set[str]:
    import ast

    import app.application.information_element_context_availability as module

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(alias.name for alias in node.names)
    return names


def test_module_imports_no_sqlalchemy_persistence_or_datetime() -> None:
    imported = _module_imported_names()
    assert not any("sqlalchemy" in name.lower() for name in imported)
    assert not any("infrastructure.persistence" in name for name in imported)
    assert "datetime" not in imported


def test_module_imports_no_forbidden_capability() -> None:
    imported = _module_imported_names()
    forbidden = {
        "GapImpactContext",
        "RelationshipContextEntry",
        "RemediationAction",
        "SourceObservation",
        "FieldValueEvidence",
    }
    assert imported.isdisjoint(forbidden)
    assert not any(name == "app.application.gap_impact_remediation" for name in imported)
    assert not any("app.integration" in name or "app.api" in name for name in imported)
    assert not any("fastapi" in name.lower() for name in imported)


def test_service_exposes_no_method_beyond_compose() -> None:
    public_methods = {
        name
        for name, _ in inspect.getmembers(
            InformationElementContextAvailabilityApplicationService, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert public_methods == {"compose"}


# ---------------------------------------------------------------------------
# 17: exact result-field shape, no Gate-N timestamp
# ---------------------------------------------------------------------------


def test_result_has_exactly_the_frozen_four_fields() -> None:
    field_names = {f.name for f in dataclasses.fields(InformationElementContextAvailabilityResult)}
    assert field_names == {
        "information_element_requirement_id",
        "obligation",
        "coverage_status",
        "evidence_availability_status",
    }


def test_result_is_frozen() -> None:
    element = _mapped_element()
    h4 = _h4_result(element=element)
    service = InformationElementContextAvailabilityApplicationService()

    result = service.compose(
        coverage_result=_coverage_result(elements=(element,)), evidence_availability_results=(h4,)
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        result[0].coverage_status = CoverageStatus.UNMAPPED  # type: ignore[misc]
