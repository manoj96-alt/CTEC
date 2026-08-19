import ast
import subprocess
from dataclasses import fields
from pathlib import Path

from app.runtime.orchestration import CapabilityStepPorts
from app.runtime.recovery import STAGES

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = REPOSITORY_ROOT / "backend" / "app" / "runtime"
AUTHORIZED_CHANGED_PATHS = {
    ".gitignore",
    "backend/Dockerfile",
    "docker-compose.yml",
    "frontend/Dockerfile",
    ".dockerignore",
    "DEMO_RUNBOOK.md",
    "DOCKER_SMOKE_TEST.md",
    "backend/.dockerignore",
    "backend/docker-entrypoint.sh",
    "frontend/.dockerignore",
    "frontend/components/supplier-risk/recommendation-panel.tsx",
    "frontend/lib/supplier-risk/contracts.ts",
    "frontend/tests/supplier-risk-recommendation.test.tsx",
    "backend/app/application/ontology_activation.py",
    "backend/app/domain/ontology/resolver.py",
    "backend/app/domain/ontology/semantic_path.py",
    "backend/app/tests/test_ontology_activation.py",
    "backend/app/tests/test_supplier_risk_ontology_activation_wiring.py",
    "backend/app/tests/test_ontology_api.py",
    "frontend/components/site-shell.tsx",
    "frontend/app/ontology-studio/page.tsx",
    "frontend/app/ontology-studio/_components/activation-card.tsx",
    "frontend/app/ontology-studio/_components/api-export-panel.tsx",
    "frontend/app/ontology-studio/_components/connector-catalog-panel.tsx",
    "frontend/app/ontology-studio/_components/ontology-graph.tsx",
    "frontend/app/ontology-studio/_components/quality-panel.tsx",
    "frontend/app/ontology-studio/_components/studio-client.tsx",
    "frontend/app/ontology-studio/_components/studio-overview.tsx",
    "frontend/lib/ontology-studio/api-client.ts",
    "frontend/lib/ontology-studio/contracts.ts",
    "frontend/tests/ontology-studio.test.tsx",
    "backend/app/api/ontology/__init__.py",
    "backend/app/api/ontology/router.py",
    "backend/app/api/ontology/schemas.py",
    "backend/app/domain/ontology/__init__.py",
    "backend/app/domain/ontology/connector_catalog.py",
    "backend/app/domain/ontology/quality_score.py",
    "backend/app/infrastructure/persistence/migrations/versions/0010_ontology_bindings.py",
    "backend/app/infrastructure/persistence/models/ontology_relationship_binding.py",
    "backend/app/infrastructure/persistence/ontology_seed.py",
    "backend/app/tests/test_ontology_quality_score.py",
    "backend/app/tests/test_ontology_seed.py",
    "README.md",
    "backend/app/runtime/__init__.py",
    "backend/app/runtime/contracts.py",
    "backend/app/runtime/engine.py",
    "backend/app/runtime/execution_state.py",
    "backend/app/runtime/execution_store.py",
    "backend/app/runtime/invocation.py",
    "backend/app/runtime/orchestration.py",
    "backend/app/tests/test_runtime_architecture.py",
    "backend/app/tests/test_runtime_contracts.py",
    "backend/app/tests/test_runtime_execution_state.py",
    "backend/app/tests/test_runtime_invocation.py",
    "backend/app/tests/test_runtime_orchestration.py",
    "backend/app/infrastructure/persistence/migrations/versions/0008_durable_execution.py",
    "backend/app/infrastructure/persistence/models/__init__.py",
    "backend/app/runtime/persistence/__init__.py",
    "backend/app/runtime/persistence/contracts.py",
    "backend/app/runtime/persistence/crypto.py",
    "backend/app/runtime/persistence/models.py",
    "backend/app/runtime/persistence/repository.py",
    "backend/app/runtime/recovery.py",
    "backend/app/tests/test_atomic_admission_postgres_concurrency.py",
    "backend/app/tests/test_durable_execution_store.py",
    "backend/app/tests/test_execution_concurrency.py",
    "backend/app/tests/test_execution_persistence_architecture.py",
    "backend/app/tests/test_execution_persistence_contracts.py",
    "backend/app/tests/test_execution_persistence_integration.py",
    "backend/app/tests/test_execution_recovery.py",
    "backend/app/tests/test_execution_replay.py",
    "backend/app/tests/test_authenticated_handoff_recovery.py",
    "backend/app/tests/test_atomic_replay_creation.py",
    "backend/app/tests/test_resume_from_stage.py",
    "backend/requirements.txt",
    "docs/cdd/CDD-010-CDD-012-REPLAY-REMEDIATION-AUTHORIZATION.md",
    "docs/cdd/CDD-010-CDD-012-Replay-Execution-Contract-Clarification-and-Remediation-Report.md",
    "docs/cdd/CDD-012-CDD-014-REPLAY-FRONTEND-DEFECT-AUTHORIZATION.md",
    "backend/app/tests/test_decision_engine.py",
    "backend/app/tests/test_governance_engine.py",
    "backend/app/tests/test_knowledge_engine.py",
    "backend/app/tests/test_persistence_integration.py",
    ".env.example",
    "backend/pyproject.toml",
    "backend/app/api/supplier_risk/__init__.py",
    "backend/app/api/supplier_risk/audit.py",
    "backend/app/api/supplier_risk/authentication.py",
    "backend/app/api/supplier_risk/dependencies.py",
    "backend/app/api/supplier_risk/errors.py",
    "backend/app/api/supplier_risk/rate_limit.py",
    "backend/app/api/supplier_risk/router.py",
    "backend/app/api/supplier_risk/schemas.py",
    "backend/app/api/supplier_risk/security.py",
    "backend/app/application/supplier_risk_api.py",
    "backend/app/core/config.py",
    "backend/app/core/dependency_container.py",
    "backend/app/infrastructure/persistence/api_security_audit_repository.py",
    "backend/app/infrastructure/persistence/migrations/versions/0009_api_security_audit.py",
    "backend/app/infrastructure/persistence/models/api_security_audit.py",
    "backend/app/main.py",
    "backend/app/tests/test_api_security_audit.py",
    "backend/app/tests/test_api_security_audit_migration.py",
    "backend/app/tests/test_oidc_authentication.py",
    "backend/app/tests/test_supplier_risk_api_architecture.py",
    "backend/app/tests/test_supplier_risk_api_commands.py",
    "backend/app/tests/test_supplier_risk_api_contracts.py",
    "backend/app/tests/test_supplier_risk_api_failures.py",
    "backend/app/tests/test_supplier_risk_api_queries.py",
    "backend/app/tests/test_supplier_risk_api_restart.py",
    "backend/app/tests/test_supplier_risk_api_security.py",
    "backend/app/tests/test_supplier_risk_api_work_queue.py",
    "backend/app/tests/test_supplier_risk_api_submission_schema.py",
    "backend/app/tests/test_supplier_risk_api_recovery_options.py",
    "backend/app/tests/test_system_api.py",
    "docs/cdd/Closure-Gate-4-CDD-013-Application-API-and-Security-Boundary-Implementation-Report.md",
    "docs/cdd/CDD-013-IMPLEMENTATION-EVIDENCE.md",
    "frontend/components/supplier-risk/replay-dialog.tsx",
    "frontend/tests/supplier-risk-recovery.test.tsx",
    # Increment 3A-0: tenant-foundation architecture release (RFC-015) and
    # the Entity Resolution tenant-ownership migration/domain/store changes
    # that depend on it.
    "architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql",
    "backend/app/core/bootstrap.py",
    "backend/app/domain/identity_resolution/model.py",
    "backend/app/domain/identity_resolution/normalization.py",
    "backend/app/domain/identity_resolution/service.py",
    "backend/app/infrastructure/persistence/entity_resolution_store.py",
    "backend/app/infrastructure/persistence/seed_loader.py",
    "backend/app/infrastructure/persistence/migrations/versions/0011_entity_resolution_tenant_and_evidence.py",
    "backend/app/infrastructure/persistence/models/enterprise_entity.py",
    "backend/app/infrastructure/persistence/models/entity_resolution.py",
    "backend/app/infrastructure/persistence/models/resolution_policy.py",
    "backend/app/infrastructure/persistence/models/source_object.py",
    "backend/app/infrastructure/persistence/models/source_system.py",
    "backend/app/integration/adapters/erm.py",
    "backend/app/tests/test_canonical_metadata.py",
    "backend/app/tests/test_entity_resolution_tenant_isolation.py",
    "backend/app/tests/test_identity_resolution_persistence.py",
    "backend/app/tests/test_identity_resolution.py",
    "docs/persistence/traceability/EAD-001-v1.6.json",
    "docs/persistence/traceability/PERSISTENCE-TRACEABILITY-v1.6.json",
    "tools/build_persistence_traceability.py",
    "tools/generate_ead_release.py",
    "tools/generate_physical_model_release.py",
    "tools/test_build_persistence_traceability.py",
    "tools/test_generate_ead_release.py",
    "tools/test_generate_physical_model_release.py",
    "architecture/INDEX.md",
    "architecture/released/v1.8/ARCHITECTURE-CONSISTENCY-REPORT-v1.9_FROZEN.md",
    "architecture/released/v1.8/DEPENDENCY-MATRIX-v1.8.csv",
    "architecture/released/v1.8/README.md",
    "architecture/released/v1.8/RELEASE-MANIFEST-v1.8.xlsx",
    "architecture/released/v1.8/RFC-015_Tenant_Ownership_Physical_Model_Authorization_v1.0_FROZEN.md",
    "scripts/verify_architecture_release.py",
    "tools/generate_release_manifest.py",
    "tools/generate_v1_8_release_manifest.py",
    "tools/test_generate_release_manifest.py",
    # Increment 3A Gate B: multi-attribute Entity Resolution evidence and
    # policy domain logic (no Steward API/frontend). Reuses Gate A's
    # persisted evidence/policy contract; no migration required.
    "backend/app/domain/identity_resolution/__init__.py",
    "backend/app/domain/identity_resolution/evidence.py",
    "backend/app/domain/identity_resolution/policy.py",
    "backend/app/infrastructure/persistence/resolution_policy_store.py",
    "backend/app/tests/test_identity_resolution_evidence.py",
    "backend/app/tests/test_identity_resolution_evidence_engine.py",
    "backend/app/tests/test_identity_resolution_gate_b_runtime_compatibility.py",
    "backend/app/tests/test_identity_resolution_normalization.py",
    "backend/app/tests/test_identity_resolution_policy.py",
    "backend/app/tests/test_resolution_policy_store.py",
    # Increment 3A Gate C: Entity Resolution Steward API (application
    # service, decision semantics, preview, router). Reuses Supplier Risk's
    # authentication/authorization/rate-limiting/audit infrastructure; no
    # migration required.
    "backend/app/api/entity_resolution/__init__.py",
    "backend/app/api/entity_resolution/dependencies.py",
    "backend/app/api/entity_resolution/router.py",
    "backend/app/api/entity_resolution/schemas.py",
    "backend/app/application/entity_resolution_steward_api.py",
    "backend/app/tests/test_entity_resolution_steward_decision.py",
    "backend/app/tests/test_entity_resolution_steward_router.py",
    "backend/app/tests/test_entity_resolution_steward_api_postgres.py",
    "backend/app/tests/test_entity_resolution_steward_concurrency_postgres.py",
    "backend/app/tests/test_entity_resolution_steward_provenance_guard.py",
    "backend/app/tests/test_entity_resolution_steward_full_stack_postgres.py",
    "backend/app/infrastructure/persistence/demo_entity_resolution_seeder.py",
    "backend/app/tests/test_demo_entity_resolution_seeder.py",
    "backend/app/tests/test_demo_entity_resolution_seeder_postgres.py",
    "frontend/lib/auth/config.ts",
    "frontend/lib/entity-resolution/api-client.ts",
    "frontend/lib/entity-resolution/contracts.ts",
    "frontend/app/ontology-studio/entity-resolution/page.tsx",
    "frontend/app/ontology-studio/entity-resolution/_components/case-detail-panel.tsx",
    "frontend/app/ontology-studio/entity-resolution/_components/case-queue.tsx",
    "frontend/app/ontology-studio/entity-resolution/_components/decision-dialog.tsx",
    "frontend/app/ontology-studio/entity-resolution/_components/entity-resolution-workspace.tsx",
    "frontend/app/ontology-studio/entity-resolution/_components/evidence-list.tsx",
    "frontend/app/ontology-studio/entity-resolution/_components/policy-preview-panel.tsx",
    "frontend/app/ontology-studio/_components/entity-resolution-link-card.tsx",
    "frontend/tests/entity-resolution-workspace.test.tsx",
    # Gate D0 -- governance-only remediation drafts (Priority 6 discovery
    # blockers). Neither document is authoritative yet; both are
    # RELEASE CANDIDATE, pending explicit Product Owner / architecture review
    # sign-off before registry publication. No runtime code is touched.
    "architecture/proposed/gate-d0/RFC-016_Institutional_Relationship_Canonical_Authorization_and_Tenant_Ownership_v1.0_RELEASE_CANDIDATE.md",
    "architecture/proposed/gate-d0/PAD-001-Product-Internal-Deterministic-Capability-Boundary-Clarification-v1.0_RELEASE_CANDIDATE.md",
    # Gate D1 -- architecture baseline v1.9 registry publication (RFC-016
    # frozen, PAD-001 Product-Internal Deterministic Capability Boundary
    # Clarification frozen) and the institutional_relationships
    # tenant-ownership migration it authorizes.
    "architecture/released/v1.9/ARCHITECTURE-CONSISTENCY-REPORT-v1.10_FROZEN.md",
    "architecture/released/v1.9/DEPENDENCY-MATRIX-v1.9.csv",
    "architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql",
    "architecture/released/v1.9/PAD-001-Product-Internal-Deterministic-Capability-Boundary-Clarification-v1.0_FROZEN.md",
    "architecture/released/v1.9/README.md",
    "architecture/released/v1.9/RELEASE-MANIFEST-v1.9.xlsx",
    "architecture/released/v1.9/RFC-016_Institutional_Relationship_Canonical_Authorization_and_Tenant_Ownership_v1.0_FROZEN.md",
    "docs/persistence/traceability/EAD-001-v1.7.json",
    "docs/persistence/traceability/PERSISTENCE-TRACEABILITY-v1.7.json",
    "tools/generate_v1_9_ead_release.py",
    "tools/generate_v1_9_physical_model_release.py",
    "tools/generate_v1_9_release_manifest.py",
    "backend/app/infrastructure/persistence/migrations/versions/0012_institutional_relationship_tenant_ownership.py",
    "backend/app/infrastructure/persistence/models/institutional_relationship.py",
    "backend/app/tests/test_institutional_relationship_tenant_migration_postgres.py",
    "backend/app/tests/test_institutional_relationship_tenant_migration_unit.py",
    # Gate D -- Ask CTEC MVP (Priority 6): deterministic, read-only,
    # non-LLM natural-language ontology exploration, authorized by RFC-016
    # and the PAD-001 Product-Internal Deterministic Capability Boundary
    # Clarification (architecture/released/v1.9/).
    "backend/app/domain/ontology_copilot/__init__.py",
    "backend/app/domain/ontology_copilot/intent.py",
    "backend/app/domain/ontology_copilot/traversal.py",
    "backend/app/domain/ontology_copilot/answer.py",
    "backend/app/infrastructure/persistence/institutional_relationship_store.py",
    "backend/app/infrastructure/persistence/demo_ontology_copilot_seeder.py",
    "backend/app/application/ontology_copilot_api.py",
    "backend/app/api/ontology_copilot/__init__.py",
    "backend/app/api/ontology_copilot/dependencies.py",
    "backend/app/api/ontology_copilot/router.py",
    "backend/app/api/ontology_copilot/schemas.py",
    "backend/app/tests/test_ontology_copilot_intent.py",
    "backend/app/tests/test_ontology_copilot_traversal.py",
    "backend/app/tests/test_ontology_copilot_answer.py",
    "backend/app/tests/test_ontology_copilot_api_postgres.py",
    "backend/app/tests/test_ontology_copilot_router.py",
    "backend/app/tests/test_ontology_copilot_full_stack_postgres.py",
    "backend/app/tests/test_demo_ontology_copilot_seeder.py",
    "backend/app/tests/test_demo_ontology_copilot_seeder_postgres.py",
    # Gate E Phase 2 -- local/demo authentication runtime wiring
    # (frontend/backend wired to the Gate E Phase 1 Keycloak substrate,
    # PAD-002, architecture/released/v1.10/).
    "frontend/next.config.ts",
    "frontend/components/session-controls.tsx",
    "frontend/tests/session-controls.test.tsx",
    "frontend/tests/browser-session.test.ts",
    "frontend/lib/auth/browser-session.ts",
    "frontend/tests/browser-session-signout.test.ts",
    "frontend/app/ontology-studio/ask/_components/ask-ctec-workspace.tsx",
    "frontend/tests/ask-ctec-workspace.test.tsx",
    "keycloak/ctec-realm.json",
    # Retained local RELEASE_CANDIDATE review-trail copy (PAD-002 governance
    # precedent) -- untracked, never staged/committed, but present in the
    # working tree throughout Gate E and therefore visible to this
    # tracked+untracked union check.
    "architecture/proposed/gate-e/PAD-002-Local-Development-Identity-Provider-and-Demo-Persona-Authorization-Boundary_v1.0_RELEASE_CANDIDATE.md",
    # Gate F F-I1 -- Decision Evaluation persistence and semantic foundation
    # (RFC-017 / PAD-003 / CDD-015 §33, architecture/released/v1.11/).
    "backend/app/infrastructure/persistence/migrations/versions/0013_decision_evaluation_group.py",
    "backend/app/infrastructure/persistence/models/decision_evaluation.py",
    "backend/app/domain/decision_engine/model.py",
    "backend/app/domain/decision_engine/__init__.py",
    "backend/app/infrastructure/persistence/decision_repository.py",
    "backend/app/application/decision_engine.py",
    "backend/app/tests/test_gate_f_semantic_foundation.py",
    # Gate F F-I2 -- governed impact and mitigation backend (CDD-015 §9-§12,
    # §33-§35, architecture/released/v1.11/), remediated per the merged
    # Gate F Governed Impact Decision Policy Clarification and Remediation
    # Report (PR #69: public repository contracts only, $10M annual-revenue
    # materiality, no lead-time/candidate-cost threshold, governed
    # high-severity/single-source facts, binary RECOMMENDED/REJECTED
    # policy, UNKNOWN != FALSE). No Gate F API, Keycloak scope enforcement,
    # KRM/DRM/GRM Gate F behavior beyond this, frontend, or production
    # seeder startup wiring.
    "backend/app/domain/decision_engine/configuration.py",
    "backend/app/infrastructure/persistence/governance_repository.py",
    "backend/app/integration/adapters/gate_f/__init__.py",
    "backend/app/integration/adapters/gate_f/krm.py",
    "backend/app/integration/adapters/gate_f/drm.py",
    "backend/app/integration/adapters/gate_f/grm.py",
    "backend/app/integration/gate_f_pipeline.py",
    "backend/app/application/supply_chain_impact_api.py",
    "backend/app/tests/test_gate_f_adapters.py",
    "backend/app/tests/test_gate_f_cardinality.py",
    "backend/app/tests/test_gate_f_traversal_orchestration.py",
    "backend/app/tests/test_gate_f_tenant_isolation.py",
    "backend/app/tests/test_gate_f_replay_recovery.py",
    "backend/app/tests/test_gate_f_repository_contracts.py",
    "backend/app/tests/test_integration_architecture.py",
    # Gate F F-I3 -- authenticated Supply Chain Impact API (CDD-015 §16,
    # §21, §32; PAD-003 §2a-§4a), plus the narrow F-I3.1 runtime-composition
    # authorization (PR #71: main.py router registration only,
    # dependency_container.py SupplyChainImpactApiService wiring only --
    # both files already present in this allowlist above). No F-I2
    # business-policy change, no frontend, no approval/execution endpoint.
    "backend/app/api/supply_chain_impact/__init__.py",
    "backend/app/api/supply_chain_impact/router.py",
    "backend/app/api/supply_chain_impact/schemas.py",
    "backend/app/api/supply_chain_impact/dependencies.py",
    "backend/app/tests/test_gate_f_api_security.py",
    # Gate F F-I4 -- deterministic governed demo data and two additive
    # read-only API projections (CDD-015 Deterministic Demo Data and
    # Read-Projection Clarification and Remediation Report, PR #73). No
    # F-I2 business-policy change, no ontology vocabulary, no Keycloak
    # change, no runtime-composition change, no frontend.
    "backend/app/infrastructure/persistence/demo_gate_f_seeder.py",
    "backend/app/tests/test_demo_gate_f_seeder.py",
    "backend/app/tests/test_demo_gate_f_seeder_postgres.py",
    # Gate F F-I5 -- governed supplier-risk frontend experience (CDD-016,
    # PR #75). Presentation only: every rendered fact/conclusion is a
    # direct projection of the existing, unmodified F-I3/F-I4 API
    # response. No backend, Keycloak, business-policy, persistence, or
    # ontology change; no approval/execution control;
    # `/demo/supplier-risk` unmodified.
    "frontend/app/supply-chain-impact/page.tsx",
    "frontend/app/supply-chain-impact/_components/risk-signal-panel.tsx",
    "frontend/app/supply-chain-impact/_components/business-impact-panel.tsx",
    "frontend/app/supply-chain-impact/_components/evidence-panel.tsx",
    "frontend/app/supply-chain-impact/_components/alternatives-panel.tsx",
    "frontend/app/supply-chain-impact/_components/recommendation-panel.tsx",
    "frontend/app/supply-chain-impact/_components/human-authority-banner.tsx",
    "frontend/lib/supply-chain-impact/api-client.ts",
    "frontend/lib/supply-chain-impact/contracts.ts",
    "frontend/tests/supply-chain-impact-api-client.test.ts",
    "frontend/tests/supply-chain-impact-accessibility.test.tsx",
    "frontend/tests/supply-chain-impact-workspace.test.tsx",
    # Gate G G2 -- CDD-017 canonical Supply Chain Blueprint requirement
    # contract persistence/domain substrate (CDD-017 §6-9; G2 Persistence
    # and Domain Artifact Authorization companion). Declarative only: no
    # runtime enforcement, no tenant_id, no API, no frontend, no
    # production seed. References existing entity_types/relationship_types
    # by ID only -- no parallel ontology vocabulary.
    "backend/app/infrastructure/persistence/migrations/versions/0014_blueprint_requirement_contract.py",
    "backend/app/infrastructure/persistence/models/blueprint.py",
    "backend/app/domain/blueprint/__init__.py",
    "backend/app/domain/blueprint/model.py",
    "backend/app/infrastructure/persistence/blueprint_repository.py",
    "backend/app/tests/test_blueprint_migration.py",
    "backend/app/tests/test_blueprint_persistence.py",
    "backend/app/tests/test_blueprint_persistence_postgres.py",
    # Gate G G3 (CDD-017 §3, §14; G3 Internal Blueprint Application Service
    # Artifact Authorization companion). Internal application-layer read
    # boundary over the unmodified G2 BlueprintRepository: no persistence,
    # domain, ORM, or migration change; no canonical seed; no conformance;
    # no HTTP surface; no tenant_id.
    "backend/app/application/blueprint_service.py",
    "backend/app/tests/test_blueprint_service.py",
    # Gate G G3.5 (CDD-017 §3, §13; G3.5 Canonical Blueprint Seed Artifact
    # Authorization companion). Canonical content only, resolved by name
    # against the already-governed ontology: no new EntityType/
    # RelationshipType, no repository/domain/ORM/migration change, no
    # conformance, no HTTP surface, no tenant_id. docker-entrypoint.sh is
    # already authorized above.
    "backend/app/infrastructure/persistence/blueprint_seed.py",
    "backend/app/tests/test_blueprint_seed.py",
}


def test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists() -> None:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    changed = set(tracked.stdout.splitlines()) | set(untracked.stdout.splitlines())
    assert changed <= AUTHORIZED_CHANGED_PATHS


def test_gate_f_introduces_no_seventh_cognitive_engine_stage() -> None:
    """CDD-015 §7, §20, §35: Gate F's new adapters plug into the existing
    six-port CDD-010/CDD-012 durable-execution and replay model unmodified
    -- no seventh stage, no change to `runtime/orchestration.py`'s
    `CapabilityStepPorts` contract or `runtime/recovery.py`'s `STAGES`
    tuple/`range(len(STAGES))` validation."""
    assert STAGES == ("ERM", "SRM", "ASM", "KRM", "DRM", "GRM")
    assert {field.name for field in fields(CapabilityStepPorts)} == {
        "erm",
        "srm",
        "asm",
        "krm",
        "drm",
        "grm",
    }

    gate_f_root = REPOSITORY_ROOT / "backend" / "app" / "integration" / "adapters" / "gate_f"
    gate_f_source = "\n".join(path.read_text() for path in gate_f_root.glob("*.py"))
    assert "CapabilityStepPort" not in gate_f_source
    assert "runtime.orchestration" not in gate_f_source


def test_runtime_imports_only_standard_library_and_runtime_modules() -> None:
    forbidden_prefixes = (
        "app.api",
        "app.application",
        "app.core",
        "app.domain",
        "app.infrastructure",
        "fastapi",
        "sqlalchemy",
        "pydantic",
    )
    for path in RUNTIME_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        imports.extend(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(
            module.startswith(forbidden_prefixes) for module in imports
        ), f"{path.name} bypasses the runtime boundary: {imports}"


def test_runtime_package_contains_only_authorized_top_level_files() -> None:
    assert {path.name for path in RUNTIME_ROOT.glob("*.py")} == {
        "__init__.py",
        "contracts.py",
        "engine.py",
        "execution_state.py",
        "execution_store.py",
        "invocation.py",
        "orchestration.py",
        "recovery.py",
    }
