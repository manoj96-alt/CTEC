"""Unit-only acceptance evidence for Gate K (CDD-026 §9-§14, §23; Decision-
Prerequisite Assessment Artifact Authorization §6-§9, §15). Proves the
classification algebra's rows 2-3, Obligation invariance, the two
structurally-invalid-input failure cases, determinism, input-immutability,
the module's own import hygiene (no Gate I/H4-service, Gate J, or Gate P
dependency), and the semantic vocabulary firewall -- entirely via hand-built
`InformationElementContextAvailabilityResult` fixtures, no PostgreSQL
dependency. Rows 1 and 4 (against the real demo fixture) are proven
separately, in `test_information_element_decision_prerequisite_assessment_postgres.py`."""

import ast
import inspect
import re
from dataclasses import fields, replace
from types import ModuleType
from uuid import UUID, uuid4

import pytest

from app.application import information_element_decision_prerequisite_assessment as gate_k_module
from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityResult,
)
from app.application.information_element_decision_prerequisite_assessment import (
    InformationElementDecisionPrerequisiteAssessmentApplicationService,
    InformationElementDecisionPrerequisiteAssessmentResult,
    PrerequisiteReasonCode,
    PrerequisiteStatus,
)
from app.application.information_element_evidence_availability import EvidenceAvailabilityStatus
from app.application.semantic_coverage_evaluation import CoverageStatus
from app.domain.blueprint import Obligation
from app.domain.shared.exceptions import ValidationException


def _context(
    *,
    obligation: Obligation,
    coverage_status: CoverageStatus,
    evidence_availability_status: EvidenceAvailabilityStatus | None,
    requirement_id: UUID | None = None,
) -> InformationElementContextAvailabilityResult:
    return InformationElementContextAvailabilityResult(
        information_element_requirement_id=requirement_id or uuid4(),
        obligation=obligation,
        coverage_status=coverage_status,
        evidence_availability_status=evidence_availability_status,
    )


# ---------------------------------------------------------------------------
# A/D. Classification algebra -- rows 2 and 3 (rows 1 and 4 proven against the
# real fixture in the companion Postgres acceptance test).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.CONDITIONAL, Obligation.OPTIONAL]
)
def test_mapped_no_evidence_is_prerequisites_incomplete(obligation: Obligation) -> None:
    context = _context(
        obligation=obligation,
        coverage_status=CoverageStatus.MAPPED,
        evidence_availability_status=EvidenceAvailabilityStatus.NO_EVIDENCE,
    )

    result = InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(
        context=context
    )

    assert result.prerequisite_status is PrerequisiteStatus.PREREQUISITES_INCOMPLETE
    assert result.reason_code is PrerequisiteReasonCode.APPROVED_MAPPING_WITH_NO_EVIDENCE_OBSERVED


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.CONDITIONAL, Obligation.OPTIONAL]
)
def test_mapped_evidence_empty_is_prerequisites_incomplete(obligation: Obligation) -> None:
    context = _context(
        obligation=obligation,
        coverage_status=CoverageStatus.MAPPED,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_EMPTY,
    )

    result = InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(
        context=context
    )

    assert result.prerequisite_status is PrerequisiteStatus.PREREQUISITES_INCOMPLETE
    assert result.reason_code is PrerequisiteReasonCode.APPROVED_MAPPING_WITH_EMPTY_EVIDENCE


# Rows 1 and 4, hand-built here too (in addition to the real-fixture Postgres
# proof), to exercise the algorithm directly and cheaply for every Obligation
# value -- the Postgres test alone only exercises Obligation.REQUIRED
# (Supplier Legal Name) and Obligation.CONDITIONAL (Risk Event Severity).


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.CONDITIONAL, Obligation.OPTIONAL]
)
def test_unmapped_none_is_not_evaluable(obligation: Obligation) -> None:
    context = _context(
        obligation=obligation,
        coverage_status=CoverageStatus.UNMAPPED,
        evidence_availability_status=None,
    )

    result = InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(
        context=context
    )

    assert result.prerequisite_status is PrerequisiteStatus.NOT_EVALUABLE
    assert result.reason_code is PrerequisiteReasonCode.NO_APPROVED_MAPPING


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.CONDITIONAL, Obligation.OPTIONAL]
)
def test_mapped_evidence_present_is_prerequisites_present(obligation: Obligation) -> None:
    context = _context(
        obligation=obligation,
        coverage_status=CoverageStatus.MAPPED,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )

    result = InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(
        context=context
    )

    assert result.prerequisite_status is PrerequisiteStatus.PREREQUISITES_PRESENT
    assert result.reason_code is PrerequisiteReasonCode.APPROVED_MAPPING_WITH_EVIDENCE_OBSERVED


# ---------------------------------------------------------------------------
# E. Obligation invariance -- explicit cross-check that classification is
# identical across all three Obligation values for each of the four rows.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "coverage_status,evidence_availability_status,expected_status,expected_reason",
    [
        (
            CoverageStatus.UNMAPPED,
            None,
            PrerequisiteStatus.NOT_EVALUABLE,
            PrerequisiteReasonCode.NO_APPROVED_MAPPING,
        ),
        (
            CoverageStatus.MAPPED,
            EvidenceAvailabilityStatus.NO_EVIDENCE,
            PrerequisiteStatus.PREREQUISITES_INCOMPLETE,
            PrerequisiteReasonCode.APPROVED_MAPPING_WITH_NO_EVIDENCE_OBSERVED,
        ),
        (
            CoverageStatus.MAPPED,
            EvidenceAvailabilityStatus.EVIDENCE_EMPTY,
            PrerequisiteStatus.PREREQUISITES_INCOMPLETE,
            PrerequisiteReasonCode.APPROVED_MAPPING_WITH_EMPTY_EVIDENCE,
        ),
        (
            CoverageStatus.MAPPED,
            EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
            PrerequisiteStatus.PREREQUISITES_PRESENT,
            PrerequisiteReasonCode.APPROVED_MAPPING_WITH_EVIDENCE_OBSERVED,
        ),
    ],
)
def test_obligation_never_changes_classification(
    coverage_status: CoverageStatus,
    evidence_availability_status: EvidenceAvailabilityStatus | None,
    expected_status: PrerequisiteStatus,
    expected_reason: PrerequisiteReasonCode,
) -> None:
    service = InformationElementDecisionPrerequisiteAssessmentApplicationService()

    results = {
        obligation: service.assess(
            context=_context(
                obligation=obligation,
                coverage_status=coverage_status,
                evidence_availability_status=evidence_availability_status,
            )
        )
        for obligation in (Obligation.REQUIRED, Obligation.CONDITIONAL, Obligation.OPTIONAL)
    }

    assert {r.prerequisite_status for r in results.values()} == {expected_status}
    assert {r.reason_code for r in results.values()} == {expected_reason}
    assert {r.obligation for r in results.values()} == {
        Obligation.REQUIRED,
        Obligation.CONDITIONAL,
        Obligation.OPTIONAL,
    }


# ---------------------------------------------------------------------------
# F/G/H. Structurally impossible Gate N combinations raise explicitly, never
# collapsing into a business classification.
# ---------------------------------------------------------------------------


def test_unmapped_with_evidence_status_raises_validation_exception() -> None:
    context = _context(
        obligation=Obligation.REQUIRED,
        coverage_status=CoverageStatus.UNMAPPED,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )

    with pytest.raises(ValidationException):
        InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(context=context)


def test_mapped_with_none_evidence_status_raises_validation_exception() -> None:
    context = _context(
        obligation=Obligation.REQUIRED,
        coverage_status=CoverageStatus.MAPPED,
        evidence_availability_status=None,
    )

    with pytest.raises(ValidationException):
        InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(context=context)


# ---------------------------------------------------------------------------
# I. Determinism.
# ---------------------------------------------------------------------------


def test_repeated_assessment_of_unchanged_input_is_identical() -> None:
    context = _context(
        obligation=Obligation.OPTIONAL,
        coverage_status=CoverageStatus.MAPPED,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )
    service = InformationElementDecisionPrerequisiteAssessmentApplicationService()

    first = service.assess(context=context)
    second = service.assess(context=context)

    assert first == second


# ---------------------------------------------------------------------------
# J. Input immutability -- the input's own frozen/slotted type makes mutation
# structurally impossible; confirmed directly and via a no-side-effect check.
# ---------------------------------------------------------------------------


def test_input_context_is_not_mutated() -> None:
    context = _context(
        obligation=Obligation.CONDITIONAL,
        coverage_status=CoverageStatus.MAPPED,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_EMPTY,
    )
    # Independent value snapshot -- a genuinely separate object (not an
    # alias of `context`), so this comparison can actually detect an
    # in-place mutation rather than trivially comparing an object to itself.
    before = replace(context)

    InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(context=context)

    assert context == before
    with pytest.raises(AttributeError):
        context.coverage_status = CoverageStatus.UNMAPPED  # type: ignore[misc]


def test_result_is_a_new_object_not_a_reference_into_the_input() -> None:
    context = _context(
        obligation=Obligation.REQUIRED,
        coverage_status=CoverageStatus.MAPPED,
        evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
    )

    result = InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(
        context=context
    )

    assert id(result) != id(context)
    assert isinstance(result, InformationElementDecisionPrerequisiteAssessmentResult)


# ---------------------------------------------------------------------------
# Result-contract shape.
# ---------------------------------------------------------------------------


def test_result_has_exactly_six_fields() -> None:
    field_names = {f.name for f in fields(InformationElementDecisionPrerequisiteAssessmentResult)}
    assert field_names == {
        "information_element_requirement_id",
        "obligation",
        "coverage_status",
        "evidence_availability_status",
        "prerequisite_status",
        "reason_code",
    }


def test_service_has_no_constructor_dependencies() -> None:
    assert InformationElementDecisionPrerequisiteAssessmentApplicationService() is not None
    assert (
        "__init__"
        not in InformationElementDecisionPrerequisiteAssessmentApplicationService.__dict__
    )


# ---------------------------------------------------------------------------
# I/J/K. Import hygiene -- no Gate I/H4-service reconstruction, no Gate J, no
# Gate P dependency anywhere in the production module.
# ---------------------------------------------------------------------------


def _module_imported_names(module: ModuleType) -> set[str]:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom | ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_production_module_imports_no_gate_i_or_h4_service_class() -> None:
    imported = _module_imported_names(gate_k_module)
    assert "SemanticCoverageEvaluationApplicationService" not in imported
    assert "InformationElementEvidenceAvailabilityApplicationService" not in imported


def test_production_module_imports_no_gate_j_dependency() -> None:
    imported = _module_imported_names(gate_k_module)
    assert not any("gap_impact_remediation" in name for name in imported)
    assert "GapImpactContext" not in imported
    assert "RemediationAction" not in imported


def test_production_module_imports_no_gate_p_dependency() -> None:
    imported = _module_imported_names(gate_k_module)
    assert not any("ontology_copilot" in name for name in imported)


def test_production_module_imports_no_persistence_or_container_dependency() -> None:
    imported = _module_imported_names(gate_k_module)
    assert not any("sqlalchemy" in name.lower() for name in imported)
    assert not any("dependency_container" in name for name in imported)
    assert not any("infrastructure.persistence" in name for name in imported)


# ---------------------------------------------------------------------------
# L. Semantic vocabulary firewall.
# ---------------------------------------------------------------------------


_FORBIDDEN_VOCABULARY = (
    "ready",
    "not_ready",
    "trust",
    "confidence",
    "quality",
    "freshness",
    "risk",
    "severity",
    "priority",
    "ranking",
    "score",
    "percentage",
    "weight",
)


def test_production_module_source_contains_no_forbidden_vocabulary() -> None:
    # CDD-026 §23 item 8 scopes this firewall to the module's own "field
    # names, enum values, or code" -- not its prose documentation. The
    # module docstring legitimately *names* the prohibited vocabulary (e.g.
    # "never a READY/NOT_READY verdict"), exactly as Gate N's own docstring
    # legitimately names "trust, confidence, freshness, or readiness" while
    # documenting what it deliberately does not do. The docstring is
    # therefore excluded from the scan; only executable code (identifiers,
    # string literals used as enum values, etc.) is checked. Word-boundary
    # matching also avoids a false positive on "already" containing "ready".
    source = inspect.getsource(gate_k_module)
    docstring = inspect.getdoc(gate_k_module) or ""
    code_only = source.replace(docstring, "", 1).lower()
    for term in _FORBIDDEN_VOCABULARY:
        pattern = rf"\b{re.escape(term)}\b"
        assert not re.search(
            pattern, code_only
        ), f"forbidden vocabulary {term!r} found in production module code"
