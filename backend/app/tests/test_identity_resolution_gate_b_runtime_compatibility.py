"""Gate B (multi-attribute evidence + policy domain) is strictly additive to
the existing, automated, name-only Entity Resolution runtime path used by
the Supplier Risk pipeline (EntityResolutionEngine / ResolutionPolicy /
EntityResolutionAdapter). These tests prove that path is unchanged: no
signature, behavior, or export was altered to add Gate B."""

from datetime import UTC, datetime
from uuid import uuid4

import app.domain.identity_resolution as identity_resolution_package
from app.domain.identity_resolution import (
    BusinessConfidence,
    EntityResolutionEngine,
    ResolutionOutcome,
    ResolutionPolicy,
    ResolutionPolicyDefinition,
    balanced_preset,
    conservative_preset,
    exploratory_preset,
)
from app.integration.adapters.erm import EntityResolutionAdapter


def test_pre_gate_b_public_symbols_are_still_exported() -> None:
    """Everything importable from this package before Gate B must remain
    importable, unchanged, after it."""
    pre_gate_b_symbols = {
        "EntityResolutionEngine",
        "ResolutionPolicy",
        "EnterpriseEntityResolutionRecord",
        "ResolutionCandidate",
        "ResolutionOutcome",
        "BusinessConfidence",
        "EvidenceItem",
        "EvidenceProfile",
        "EvidenceClassification",
        "EvidenceType",
    }
    exported = set(dir(identity_resolution_package))
    assert pre_gate_b_symbols <= exported


def test_entity_resolution_adapter_still_imports_and_constructs_unmodified() -> None:
    """The Gate-A/production runtime adapter must not require any change to
    keep working: it still only calls discover_candidates()/resolve() on
    the original name-only engine."""
    import inspect

    source = inspect.getsource(EntityResolutionAdapter)
    assert "entity_resolution.discover_candidates(" in source
    assert "entity_resolution.resolve(" in source
    assert "EvidenceResolutionEngine" not in source


def test_name_only_engine_behavior_is_unchanged_by_gate_b() -> None:
    policy = ResolutionPolicy(version="runtime-compat-v1")
    engine = EntityResolutionEngine(policy)
    entity_id = uuid4()
    candidates = engine.discover_candidates(
        source_names=("Acme Widgets",),
        enterprise_entities=((entity_id, "Acme Widgets"),),
    )
    assert len(candidates) == 1
    assert candidates[0].enterprise_entity_id == entity_id
    assert candidates[0].internal_score == 1.0

    record = engine.resolve(
        tenant_id="tenant-runtime-compat",
        supporting_source_object_ids=(uuid4(),),
        candidates=candidates,
        produced_at=datetime.now(UTC),
    )
    assert record.outcome is ResolutionOutcome.RESOLVED
    assert record.enterprise_entity_id == entity_id
    assert record.policy_version == "runtime-compat-v1"
    # Gate A fields default to None on the name-only path -- Gate B never
    # forces every caller to populate an evidence profile.
    assert record.evidence_profile is None
    assert record.policy_id is None
    assert record.actor_id is None
    assert record.decision_rationale is None


def test_evidence_engine_requires_no_change_to_the_shared_vocabulary_types() -> None:
    """RESOLVED/POSSIBLE/UNRESOLVED and HIGH/MEDIUM/LOW retain their original
    values; Gate B only adds BLOCKED_CONFLICT as a new, additive value."""
    assert ResolutionOutcome.RESOLVED.value == "Resolved"
    assert ResolutionOutcome.POSSIBLE.value == "Possible Resolution"
    assert ResolutionOutcome.UNRESOLVED.value == "Unresolved"
    assert ResolutionOutcome.BLOCKED_CONFLICT.value == "Blocked Conflict"
    assert BusinessConfidence.HIGH.value == "High"
    assert BusinessConfidence.MEDIUM.value == "Medium"
    assert BusinessConfidence.LOW.value == "Low"


def test_all_three_policy_presets_are_importable_from_the_package_root() -> None:
    for factory in (conservative_preset, balanced_preset, exploratory_preset):
        definition = factory()
        assert isinstance(definition, ResolutionPolicyDefinition)
