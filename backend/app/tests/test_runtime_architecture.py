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
    # Gate G G4 (CDD-018 §6-16; G4 Blueprint Conformance Artifact
    # Authorization companion). Structural conformance evaluation only,
    # read-only against tenant-scoped enterprise_entities/
    # institutional_relationships: no persistence, migration, or ORM
    # change; no InformationElementRequirement evaluation; no source
    # mapping; no HTTP surface; no BlueprintSeeder runtime dependency.
    # blueprint_repository.py, application/blueprint_service.py,
    # test_blueprint_service.py, and test_blueprint_persistence_postgres.py
    # are already authorized above.
    "backend/app/infrastructure/persistence/blueprint_conformance_context_store.py",
    "backend/app/application/blueprint_conformance.py",
    "backend/app/tests/test_blueprint_conformance.py",
    # Gate H H1 (CDD-019 §7, §8, §11; H1 Source Field / Semantic Mapping
    # Artifact Authorization companion). SourceField/SemanticMapping
    # domain/persistence foundation only: no H2 resolution service, no H3
    # demo seeder, no H4 conformance integration; no Blueprint modification;
    # InformationElementRequirement remains NOT_EVALUATED.
    "backend/app/domain/integration/source_field.py",
    "backend/app/domain/integration/__init__.py",
    "backend/app/domain/semantic_mapping/__init__.py",
    "backend/app/domain/semantic_mapping/model.py",
    "backend/app/infrastructure/persistence/models/source_field.py",
    "backend/app/infrastructure/persistence/models/semantic_mapping.py",
    "backend/app/infrastructure/persistence/migrations/versions/0015_source_field_semantic_mapping.py",
    "backend/app/infrastructure/persistence/source_field_repository.py",
    "backend/app/infrastructure/persistence/semantic_mapping_repository.py",
    "backend/app/tests/test_source_field_persistence.py",
    "backend/app/tests/test_source_field_persistence_postgres.py",
    "backend/app/tests/test_semantic_mapping_persistence.py",
    "backend/app/tests/test_semantic_mapping_persistence_postgres.py",
    # H1 companion remediation (row 19): test_domain_foundation.py's
    # declared_classes exact-set assertion required "SourceField" once row 1
    # placed it in domain/integration/ (one of the five canonical domain
    # roots that test enumerates) -- authorized narrowly, one string, one
    # set, one test function only.
    "backend/app/tests/test_domain_foundation.py",
    # H2 companion: SemanticMappingResolutionApplicationService (new file)
    # and its unit tests (new file). Neither existed before H2.
    "backend/app/application/semantic_mapping_resolution.py",
    "backend/app/tests/test_semantic_mapping_resolution.py",
    # H3 companion: DemoSemanticMappingSeeder (new file) and its unit +
    # Postgres tests (new files). None existed before H3.
    "backend/app/infrastructure/persistence/demo_semantic_mapping_seeder.py",
    "backend/app/tests/test_demo_semantic_mapping_seeder.py",
    "backend/app/tests/test_demo_semantic_mapping_seeder_postgres.py",
    # Gate I I1 companion: SemanticCoverageEvaluationApplicationService (new
    # file) and its unit + Postgres tests (new files). None existed before I1.
    "backend/app/application/semantic_coverage_evaluation.py",
    "backend/app/tests/test_semantic_coverage_evaluation.py",
    "backend/app/tests/test_semantic_coverage_evaluation_postgres.py",
    # Gate J J1/J2 companion: GapImpactRemediationApplicationService (new
    # file) and its unit + Postgres tests (new files). None existed before J1/J2.
    "backend/app/application/gap_impact_remediation.py",
    "backend/app/tests/test_gap_impact_remediation.py",
    "backend/app/tests/test_gap_impact_remediation_postgres.py",
    # CDD-022 companion: FieldValueEvidence domain/persistence/migration/
    # seeder (new files) and its unit + Postgres tests (new files). The
    # mechanical migration-head consequence in test_decision_engine.py/
    # test_governance_engine.py/test_knowledge_engine.py/
    # test_persistence_integration.py needs no new entry here -- each was
    # already added permanently above by an earlier gate for the identical
    # reason (every migration bump touches these four).
    "backend/app/domain/integration/field_value_evidence.py",
    "backend/app/infrastructure/persistence/models/field_value_evidence.py",
    "backend/app/infrastructure/persistence/field_value_evidence_repository.py",
    "backend/app/infrastructure/persistence/migrations/versions/0016_field_value_evidence.py",
    "backend/app/infrastructure/persistence/demo_field_value_evidence_seeder.py",
    "backend/app/tests/test_field_value_evidence_persistence.py",
    "backend/app/tests/test_field_value_evidence_persistence_postgres.py",
    "backend/app/tests/test_demo_field_value_evidence_seeder.py",
    "backend/app/tests/test_demo_field_value_evidence_seeder_postgres.py",
    # H4 companion: InformationElementEvidenceAvailabilityApplicationService
    # (new file) and its unit + Postgres tests (new files). None existed
    # before H4.
    "backend/app/application/information_element_evidence_availability.py",
    "backend/app/tests/test_information_element_evidence_availability.py",
    "backend/app/tests/test_information_element_evidence_availability_postgres.py",
    # Gate N companion: InformationElementContextAvailabilityApplicationService
    # (new file) and its unit + Postgres tests (new files). None existed
    # before Gate N.
    "backend/app/application/information_element_context_availability.py",
    "backend/app/tests/test_information_element_context_availability.py",
    "backend/app/tests/test_information_element_context_availability_postgres.py",
    # Gate K companion: InformationElementDecisionPrerequisiteAssessmentApplicationService
    # (new file) and its unit + Postgres tests (new files). None existed
    # before Gate K.
    "backend/app/application/information_element_decision_prerequisite_assessment.py",
    "backend/app/tests/test_information_element_decision_prerequisite_assessment.py",
    "backend/app/tests/test_information_element_decision_prerequisite_assessment_postgres.py",
    # Gate L6 companion: SemanticMappingCandidateUniverseService /
    # SemanticMappingProposalGovernanceApplicationService (new files) and
    # their unit + Postgres tests (new files). None existed before Gate L
    # (CDD-027; AI-Assisted Semantic Mapping Candidate Discovery Artifact
    # Authorization, as corrected by the Human-Approver Attribution
    # Clarification and Remediation Report).
    "backend/app/application/semantic_mapping_candidate_discovery.py",
    "backend/app/application/semantic_mapping_proposal_governance.py",
    "backend/app/tests/test_semantic_mapping_candidate_discovery.py",
    "backend/app/tests/test_semantic_mapping_proposal_governance.py",
    "backend/app/tests/test_semantic_mapping_proposal_lifecycle_postgres.py",
    # Gate M companion: Governed Visual Ontology Modeling, net-new-only
    # (CDD-028; Gate M Artifact Authorization v1.1). New non-canonical
    # OntologyChangeProposal domain/persistence/migration/repository,
    # application governance service, and API package (new files), plus
    # their unit + Postgres + router tests (new files). None existed before
    # Gate M. entity_types/relationship_types/institutional_concepts/
    # ontology_relationship_bindings and resolver.py remain unmodified.
    "backend/app/domain/ontology_modeling/__init__.py",
    "backend/app/domain/ontology_modeling/proposal.py",
    "backend/app/infrastructure/persistence/models/ontology_change_proposal.py",
    "backend/app/infrastructure/persistence/migrations/versions/0017_ontology_change_proposal.py",
    "backend/app/infrastructure/persistence/ontology_change_proposal_repository.py",
    "backend/app/application/ontology_modeling_proposal_governance.py",
    "backend/app/api/ontology_modeling/__init__.py",
    "backend/app/api/ontology_modeling/router.py",
    "backend/app/api/ontology_modeling/schemas.py",
    "backend/app/api/ontology_modeling/dependencies.py",
    "backend/app/tests/test_ontology_modeling_proposal_governance.py",
    "backend/app/tests/test_ontology_modeling_proposal_lifecycle_postgres.py",
    "backend/app/tests/test_ontology_modeling_router.py",
    # Gate M frontend companion (Gate M Artifact Authorization v1.1 §11):
    # self-contained new /ontology-studio/ontology-modeling sub-route (new
    # files), mirroring the existing entity-resolution sub-workspace shape.
    # No modification to ontology-graph.tsx or lib/ontology-studio/*.
    "frontend/lib/ontology-modeling/api-client.ts",
    "frontend/lib/ontology-modeling/contracts.ts",
    "frontend/app/ontology-studio/ontology-modeling/page.tsx",
    "frontend/app/ontology-studio/ontology-modeling/_components/ontology-modeling-workspace.tsx",
    "frontend/app/ontology-studio/ontology-modeling/_components/propose-form.tsx",
    "frontend/app/ontology-studio/ontology-modeling/_components/proposal-list.tsx",
    "frontend/app/ontology-studio/ontology-modeling/_components/decision-dialog.tsx",
    "frontend/app/ontology-studio/_components/ontology-modeling-link-card.tsx",
    "frontend/tests/ontology-modeling-workspace.test.tsx",
    # Gate O companion: Governed Blueprint Information-Element
    # Context-as-a-Service (CDD-029; Gate O Artifact Authorization v1.0).
    # New, standalone application service reusing the existing, unmodified
    # Blueprint/Gate I/H4/Gate N chain by call only, plus a new, dedicated
    # API package (new files), plus their unit + Postgres + router tests
    # (new files). Ask CTEC (ontology_copilot_api.py and its router/schemas)
    # remains completely untouched; the resulting orchestration-logic
    # duplication is an explicit, Product-Owner-accepted tradeoff.
    "backend/app/application/information_element_context_resolution.py",
    "backend/app/api/information_element_context/__init__.py",
    "backend/app/api/information_element_context/router.py",
    "backend/app/api/information_element_context/schemas.py",
    "backend/app/api/information_element_context/dependencies.py",
    "backend/app/tests/test_information_element_context_resolution.py",
    "backend/app/tests/test_information_element_context_resolution_postgres.py",
    "backend/app/tests/test_information_element_context_router.py",
    # Gate Q companion: Governed Outbound MCP Client and Connector
    # Capability Boundary (CDD-030; Gate Q Artifact Authorization v1.0).
    # New, standalone, router-less MCP client and static tool/connector
    # catalog -- no persistence, no migration, no API, no frontend, no new
    # dependency. backend/app/domain/ontology/connector_catalog.py remains
    # completely untouched and independent (Q-D5).
    "backend/app/application/mcp_connector_catalog.py",
    "backend/app/application/mcp_client.py",
    "backend/app/tests/test_mcp_connector_catalog.py",
    "backend/app/tests/test_mcp_client.py",
    # Gate T companion: Governed Source-Evidence Fitness Evaluation and
    # Ontology Impact (CDD-031; Gate T Artifact Authorization v1.0). New,
    # standalone fitness-evaluation and impact/remediation application
    # services (new files) and their unit + Postgres tests (new files) --
    # no persistence, no migration, no API, no frontend, no new dependency.
    # gap_impact_remediation.py and information_element_evidence_availability.py
    # remain completely untouched and independent.
    "backend/app/application/source_evidence_fitness_evaluation.py",
    "backend/app/application/source_evidence_fitness_impact_remediation.py",
    "backend/app/tests/test_source_evidence_fitness_evaluation.py",
    "backend/app/tests/test_source_evidence_fitness_evaluation_postgres.py",
    "backend/app/tests/test_source_evidence_fitness_impact_remediation.py",
    "backend/app/tests/test_source_evidence_fitness_impact_remediation_postgres.py",
    # Gate U companion: Ephemeral Governed What-if Simulation over
    # Source-Evidence Fitness Impact and Remediation (CDD-032; Gate U
    # Artifact Authorization v1.0). New, standalone, zero-I/O application
    # service wrapping Gate T's own unmodified
    # SourceEvidenceFitnessImpactRemediationApplicationService by call
    # only -- no persistence, no migration, no API, no frontend, no new
    # dependency, no MCP. source_evidence_fitness_impact_remediation.py
    # remains completely untouched and independent.
    "backend/app/application/what_if_simulation.py",
    "backend/app/tests/test_what_if_simulation.py",
    # CDD-034: Governed Evidence Fitness Exposure (CDD-031 Evidence Fitness
    # Exposure Clarification and Remediation Report; CDD-034 Artifact
    # Authorization v1.0). New, standalone, thin composition/exposure
    # application service and API package exposing Gate T's own unmodified
    # SourceEvidenceFitnessEvaluationApplicationService by call only, via
    # Gate I/H4 composition -- no persistence, no migration, no frontend, no
    # dependency_container.py change, no new dependency. Gate O, Gate I, H4,
    # and Gate T remain completely untouched and independent.
    "backend/app/application/information_element_evidence_fitness_resolution.py",
    "backend/app/api/information_element_evidence_fitness/__init__.py",
    "backend/app/api/information_element_evidence_fitness/router.py",
    "backend/app/api/information_element_evidence_fitness/schemas.py",
    "backend/app/api/information_element_evidence_fitness/dependencies.py",
    "backend/app/tests/test_information_element_evidence_fitness_resolution.py",
    "backend/app/tests/test_information_element_evidence_fitness_resolution_postgres.py",
    "backend/app/tests/test_information_element_evidence_fitness_router.py",
    # GAP-8 companion: Evidence Fitness Frontend Exposure Authorization
    # (CDD-034 Evidence Fitness Frontend Exposure Authorization §11). Pure
    # frontend consumption of the existing, unmodified CDD-034 resolve
    # endpoint -- new API client and contracts (new files), the existing
    # disconnected page rewritten to a live interaction, and its test (new
    # file). No backend production file, no Keycloak file, no migration.
    "frontend/lib/evidence-fitness/api-client.ts",
    "frontend/lib/evidence-fitness/contracts.ts",
    "frontend/app/quality/evidence-fitness/page.tsx",
    "frontend/tests/evidence-fitness-workspace.test.tsx",
    # GAP-8 R5-A Product Owner sixth-file amendment: reconciling the
    # pre-existing Gate X honesty assertion with the already-approved
    # CDD-034 Evidence Fitness Frontend Exposure Authorization's live
    # consumer contract. No other Gate X honesty assertion is touched.
    "frontend/tests/gate-x-honesty.test.tsx",
    # Gate R (CDD-035) v1 implementation: the GovernedToolExecutor
    # application module and its focused test file. No other file in this
    # allowlist is touched by Gate R.
    "backend/app/application/governed_tool_executor.py",
    "backend/app/tests/test_governed_tool_executor.py",
    # Gate S (CDD-036) v1 implementation: Governed Human Approval. No Gate R
    # file above is touched by Gate S.
    "backend/app/domain/gate_s/__init__.py",
    "backend/app/domain/gate_s/approval.py",
    "backend/app/infrastructure/persistence/models/gate_s_approval.py",
    "backend/app/infrastructure/persistence/migrations/versions/0018_gate_s_approval.py",
    "backend/app/infrastructure/persistence/gate_s_approval_repository.py",
    "backend/app/application/gate_s_approval_service.py",
    "backend/app/api/gate_s/__init__.py",
    "backend/app/api/gate_s/dependencies.py",
    "backend/app/api/gate_s/schemas.py",
    "backend/app/api/gate_s/router.py",
    "backend/app/tests/test_gate_s_approval_service.py",
    "backend/app/tests/test_gate_s_approval_router.py",
    "backend/app/tests/test_gate_s_approval_postgres.py",
    "docs/cdd/CDD-036-Governed-Human-Approval.md",
    "docs/cdd/CDD-036-Governed-Human-Approval-Artifact-Authorization.md",
    # Gate V (CDD-037) v1 implementation: Governed Agent Resolution. No Gate
    # Q, Gate R, or Gate S file above is touched by Gate V. The mechanical
    # migration-head consequence in test_decision_engine.py/
    # test_governance_engine.py/test_knowledge_engine.py/
    # test_persistence_integration.py needs no new entry here -- each was
    # already added permanently above by an earlier gate for the identical
    # reason (every migration bump touches these four).
    "backend/app/domain/gate_v/__init__.py",
    "backend/app/domain/gate_v/agent_resolution.py",
    "backend/app/infrastructure/persistence/models/gate_v_agent_resolution.py",
    "backend/app/infrastructure/persistence/migrations/versions/0019_gate_v_agent_resolution.py",
    "backend/app/infrastructure/persistence/gate_v_agent_resolution_repository.py",
    "backend/app/application/gate_v_agent_service.py",
    "backend/app/api/gate_v/__init__.py",
    "backend/app/api/gate_v/dependencies.py",
    "backend/app/api/gate_v/schemas.py",
    "backend/app/api/gate_v/router.py",
    "backend/app/tests/test_gate_v_agent_service.py",
    "backend/app/tests/test_gate_v_agent_router.py",
    "backend/app/tests/test_gate_v_agent_postgres.py",
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


def test_gate_r_governed_tool_executor_respects_every_firewall() -> None:
    """CDD-035 Sec29, Sec30: Gate R (Governed Tool Execution) is structurally
    independent from Gate Q's MCP client/catalog and from the closed
    six-stage cognitive-engine runtime. It introduces no seventh stage and
    depends on no external provider SDK."""
    module_path = REPOSITORY_ROOT / "backend" / "app" / "application" / "governed_tool_executor.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
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

    # `app.api.supplier_risk.authentication` (TrustedPrincipal) is the sole
    # authorized exception (CDD-035 Sec11, Artifact Authorization Sec6) --
    # no other `app.api.*` module (no router, no new API surface) may be
    # imported.
    forbidden_prefixes = (
        "app.application.mcp_client",
        "app.application.mcp_connector_catalog",
        "app.runtime",
        "app.integration.adapters",
        "openai",
        "anthropic",
        "azure",
    )
    assert not any(
        module.startswith(forbidden_prefixes) for module in imports
    ), f"governed_tool_executor.py bypasses a Gate R firewall: {imports}"
    assert all(
        not module.startswith("app.api") or module == "app.api.supplier_risk.authentication"
        for module in imports
    ), f"governed_tool_executor.py imports an unauthorized API module: {imports}"

    assert STAGES == ("ERM", "SRM", "ASM", "KRM", "DRM", "GRM")

    from app.application.governed_tool_executor import GOVERNED_TOOL_REGISTRY

    assert len(GOVERNED_TOOL_REGISTRY) == 1
    assert GOVERNED_TOOL_REGISTRY[0].side_effect_class == "READ_ONLY"


def test_gate_s_governed_approval_respects_every_firewall() -> None:
    """CDD-036 Sec21-Sec22, Sec29, Sec32-Sec33: Gate S shares no code with
    Gate R, Gate Q, or the closed six-stage cognitive-engine runtime, and
    `GateSGovernedNoteORM` is constructed in exactly one location in the
    entire codebase."""
    gate_s_paths = (
        REPOSITORY_ROOT / "backend" / "app" / "domain" / "gate_s" / "approval.py",
        REPOSITORY_ROOT
        / "backend"
        / "app"
        / "infrastructure"
        / "persistence"
        / "gate_s_approval_repository.py",
        REPOSITORY_ROOT / "backend" / "app" / "application" / "gate_s_approval_service.py",
        REPOSITORY_ROOT / "backend" / "app" / "api" / "gate_s" / "dependencies.py",
        REPOSITORY_ROOT / "backend" / "app" / "api" / "gate_s" / "router.py",
    )
    forbidden_prefixes = (
        "app.application.mcp_client",
        "app.application.mcp_connector_catalog",
        "app.application.governed_tool_executor",
        "app.runtime",
        "app.integration.adapters",
        "openai",
        "anthropic",
        "azure",
    )
    for path in gate_s_paths:
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
        ), f"{path.name} bypasses a Gate S firewall: {imports}"

    backend_root = REPOSITORY_ROOT / "backend" / "app"
    construction_sites = [
        path
        for path in backend_root.rglob("*.py")
        if "GateSGovernedNoteORM(" in path.read_text(encoding="utf-8")
        and path.name not in {"gate_s_approval.py", "test_runtime_architecture.py"}
    ]
    assert [str(p.relative_to(backend_root)) for p in construction_sites] == [
        "infrastructure/persistence/gate_s_approval_repository.py"
    ], f"GateSGovernedNoteORM constructed outside its single authorized site: {construction_sites}"


def test_gate_v_governed_agent_resolution_respects_every_firewall() -> None:
    """CDD-037 Sec12, Sec20, Sec24-Sec27: Gate V shares no code with Gate Q,
    Gate R, or the closed six-stage cognitive-engine runtime; consumes Gate
    S only via `GateSApprovalService.request()` (never `approve()`/
    `reject()`/`decide()`/`execute()`); and `GateVAgentResolutionORM` is
    constructed in exactly one location in the entire codebase."""
    gate_v_paths = (
        REPOSITORY_ROOT / "backend" / "app" / "domain" / "gate_v" / "agent_resolution.py",
        REPOSITORY_ROOT
        / "backend"
        / "app"
        / "infrastructure"
        / "persistence"
        / "gate_v_agent_resolution_repository.py",
        REPOSITORY_ROOT / "backend" / "app" / "application" / "gate_v_agent_service.py",
        REPOSITORY_ROOT / "backend" / "app" / "api" / "gate_v" / "dependencies.py",
        REPOSITORY_ROOT / "backend" / "app" / "api" / "gate_v" / "router.py",
    )
    forbidden_prefixes = (
        "app.application.mcp_client",
        "app.application.mcp_connector_catalog",
        "app.application.governed_tool_executor",
        "app.runtime",
        "app.integration.adapters",
        "openai",
        "anthropic",
        "azure",
    )
    forbidden_gate_s_calls = (".approve(", ".reject(", ".decide(", ".execute(")
    for path in gate_v_paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
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
        ), f"{path.name} bypasses a Gate V firewall: {imports}"
        assert not any(
            call in source for call in forbidden_gate_s_calls
        ), f"{path.name} calls a Gate S human-decision/execution method: {source}"

    backend_root = REPOSITORY_ROOT / "backend" / "app"
    construction_sites = [
        path
        for path in backend_root.rglob("*.py")
        if "GateVAgentResolutionORM(" in path.read_text(encoding="utf-8")
        and path.name not in {"gate_v_agent_resolution.py", "test_runtime_architecture.py"}
    ]
    assert [str(p.relative_to(backend_root)) for p in construction_sites] == [
        "infrastructure/persistence/gate_v_agent_resolution_repository.py"
    ], f"GateVAgentResolutionORM constructed outside its single authorized site: {construction_sites}"
