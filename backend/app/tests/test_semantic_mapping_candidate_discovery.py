"""Unit-only acceptance evidence for Gate L candidate discovery (CDD-027
§11.1, §14, §16-§18; AI-Assisted Semantic Mapping Candidate Discovery
Artifact Authorization §4.1). Proves the untrusted-candidate contract's
minimality, the provider Protocol's shape, a deterministic test-local fake
provider, and the production module's own import hygiene -- entirely
without a database. Real, tenant-scoped `SourceField` universe-construction
correctness (`SemanticMappingCandidateUniverseService.build_context`) is
proven separately, against real fixture data, in
`test_semantic_mapping_proposal_lifecycle_postgres.py`."""

import ast
import inspect
from dataclasses import fields
from uuid import uuid4

from app.application import semantic_mapping_candidate_discovery as gate_l_discovery_module
from app.application.semantic_mapping_candidate_discovery import (
    CandidateDiscoveryContext,
    CandidateSelection,
    CandidateSourceField,
    SemanticMappingCandidateProvider,
)
from app.domain.blueprint import Obligation

# ---------------------------------------------------------------------------
# Untrusted-candidate contract minimality.
# ---------------------------------------------------------------------------


def test_candidate_selection_has_exactly_one_field() -> None:
    field_names = {f.name for f in fields(CandidateSelection)}
    assert field_names == {"source_field_id"}


def test_candidate_selection_carries_no_target_confidence_or_governance_fields() -> None:
    field_names = {f.name for f in fields(CandidateSelection)}
    for forbidden in (
        "information_element_requirement_id",
        "confidence",
        "rank",
        "explanation",
        "governance_status",
        "tenant_id",
        "created_by",
    ):
        assert forbidden not in field_names


def test_candidate_discovery_context_owns_the_target_not_the_provider() -> None:
    context = CandidateDiscoveryContext(
        information_element_requirement_id=uuid4(),
        element_name="Supplier Legal Name",
        description="Legal name of the supplier entity",
        obligation=Obligation.REQUIRED,
        candidate_source_fields=(),
    )
    # The target is fixed by CTEC when the context is built; CandidateSelection
    # has no field through which a provider could redefine it.
    assert context.information_element_requirement_id is not None
    assert "information_element_requirement_id" not in {f.name for f in fields(CandidateSelection)}


# ---------------------------------------------------------------------------
# Provider Protocol shape + deterministic test-local fake.
# ---------------------------------------------------------------------------


class _DeterministicFakeProvider:
    """Test-local fake implementation of SemanticMappingCandidateProvider,
    authorized by CDD-027 Decision L4-D1: confined entirely to this test
    file, never imported by production code. Selects the first candidate
    whose field_label matches a configured target label, or abstains."""

    def __init__(self, *, target_field_label: str | None) -> None:
        self._target_field_label = target_field_label

    def discover(self, *, context: CandidateDiscoveryContext) -> CandidateSelection | None:
        for candidate in context.candidate_source_fields:
            if candidate.field_label == self._target_field_label:
                return CandidateSelection(source_field_id=candidate.source_field_id)
        return None


def _candidate(field_label: str) -> CandidateSourceField:
    return CandidateSourceField(
        source_field_id=uuid4(),
        field_label=field_label,
        source_object_id=uuid4(),
        source_object_name="LFA1",
        source_system_id=uuid4(),
        source_system_name="H3 Demo ERP",
    )


def test_fake_provider_selects_matching_candidate_from_supplied_universe() -> None:
    match = _candidate("NAME1")
    other = _candidate("LAND1")
    context = CandidateDiscoveryContext(
        information_element_requirement_id=uuid4(),
        element_name="Supplier Legal Name",
        description="Legal name of the supplier entity",
        obligation=Obligation.REQUIRED,
        candidate_source_fields=(other, match),
    )
    provider: SemanticMappingCandidateProvider = _DeterministicFakeProvider(
        target_field_label="NAME1"
    )

    selection = provider.discover(context=context)

    assert selection is not None
    assert selection.source_field_id == match.source_field_id


def test_fake_provider_abstains_when_no_credible_candidate_exists() -> None:
    context = CandidateDiscoveryContext(
        information_element_requirement_id=uuid4(),
        element_name="Supplier Legal Name",
        description="Legal name of the supplier entity",
        obligation=Obligation.REQUIRED,
        candidate_source_fields=(_candidate("UNRELATED_FIELD"),),
    )
    provider: SemanticMappingCandidateProvider = _DeterministicFakeProvider(
        target_field_label="NAME1"
    )

    selection = provider.discover(context=context)

    assert selection is None


def test_fake_provider_abstains_on_empty_candidate_universe() -> None:
    context = CandidateDiscoveryContext(
        information_element_requirement_id=uuid4(),
        element_name="Supplier Legal Name",
        description="Legal name of the supplier entity",
        obligation=Obligation.REQUIRED,
        candidate_source_fields=(),
    )
    provider: SemanticMappingCandidateProvider = _DeterministicFakeProvider(
        target_field_label="NAME1"
    )

    assert provider.discover(context=context) is None


def test_fake_provider_can_only_select_from_the_supplied_universe() -> None:
    # A fake configured to "want" a label that does not exist in the
    # universe cannot fabricate a CandidateSelection for it -- it can only
    # return an id already present in candidate_source_fields, or abstain.
    context = CandidateDiscoveryContext(
        information_element_requirement_id=uuid4(),
        element_name="Supplier Legal Name",
        description="Legal name of the supplier entity",
        obligation=Obligation.REQUIRED,
        candidate_source_fields=(_candidate("NAME1"),),
    )
    provider: SemanticMappingCandidateProvider = _DeterministicFakeProvider(
        target_field_label="HALLUCINATED_FIELD"
    )

    assert provider.discover(context=context) is None


# ---------------------------------------------------------------------------
# Production-module import hygiene.
# ---------------------------------------------------------------------------


def _module_imported_names(module: object) -> set[str]:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom | ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_production_module_imports_no_gate_j_or_gate_p_dependency() -> None:
    imported = _module_imported_names(gate_l_discovery_module)
    assert not any("gap_impact_remediation" in name for name in imported)
    assert not any("ontology_copilot" in name for name in imported)


def test_production_module_imports_no_field_value_evidence() -> None:
    imported = _module_imported_names(gate_l_discovery_module)
    assert not any("field_value_evidence" in name.lower() for name in imported)


def test_production_module_imports_no_ai_sdk_or_model_provider() -> None:
    imported = _module_imported_names(gate_l_discovery_module)
    forbidden_substrings = ("openai", "anthropic", "langchain", "azure")
    for name in imported:
        lowered = name.lower()
        assert not any(term in lowered for term in forbidden_substrings)


def test_production_module_performs_no_write_operation() -> None:
    source = inspect.getsource(gate_l_discovery_module)
    assert "session.add(" not in source
    assert "session.commit(" not in source
    assert "session.delete(" not in source
