-- ============================================================
-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.7
-- Canonical core derived from ECOM Physical Data Model v1.6
-- (architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql), which
-- remains frozen and unmodified for historical traceability.
--
-- Authorized by CTEC Product Owner Manoj Nair on 2026-08-15 for
-- Gate D1 (see RFC-016, architecture/released/v1.9/). See
-- tools/generate_v1_9_physical_model_release.py for the single,
-- explicitly authorized change this release makes relative to v1.6:
-- tenant ownership on institutional_relationships.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------- Enumerated types ----------
CREATE TYPE lifecyclestate_t AS ENUM ('Draft', 'Active', 'Suspended', 'Archived');
CREATE TYPE governancestatus_t AS ENUM ('Proposed', 'Approved', 'Retired', 'Archived');
CREATE TYPE assertiontype_t AS ENUM ('Evidence-backed', 'Institutional');
CREATE TYPE decisionstatestatus_t AS ENUM ('Proposed', 'Approved', 'Not Authorized', 'Deferred', 'Superseded');
CREATE TYPE occasionlifecycle_t AS ENUM ('Recognized', 'Active', 'Consumed', 'Expired', 'Withdrawn');

-- ========== Enterprise ==========
CREATE TABLE enterprises (
    enterprise_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_name VARCHAR(200) NOT NULL UNIQUE,
    legal_name VARCHAR(300),
    enterprise_type_id UUID NOT NULL,
    country_id UUID NOT NULL,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Enterprise Type ==========
CREATE TABLE enterprise_types (
    enterprise_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) NOT NULL UNIQUE
);
-- OPEN DECISION: type_name -- global vs. per-enterprise not yet decided

-- ========== Country ==========
CREATE TABLE countries (
    country_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_name VARCHAR(100) NOT NULL UNIQUE,
    iso2_code VARCHAR(2) NOT NULL UNIQUE,
    iso3_code VARCHAR(3) NOT NULL UNIQUE
);

-- ========== Business Domain ==========
CREATE TABLE business_domains (
    business_domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID NOT NULL,
    domain_name VARCHAR(150) NOT NULL,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Institutional Concept ==========
CREATE TABLE institutional_concepts (
    institutional_concept_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institutional_concept_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    enterprise_id UUID NOT NULL
);

-- ========== Relationship Type ==========
CREATE TABLE relationship_types (
    relationship_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_type_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Entity Type ==========
CREATE TABLE entity_types (
    entity_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    institutional_concept_id UUID NOT NULL
);

-- ========== Enterprise Entity ==========
CREATE TABLE enterprise_entities (
    enterprise_entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    enterprise_entity_name VARCHAR(200) NOT NULL,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    entity_type_id UUID NOT NULL,
    business_domain_id UUID NOT NULL
);

-- ========== Evidence ==========
CREATE TABLE evidences (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    source_object_id UUID
);

-- ========== Assertion ==========
CREATE TABLE assertions (
    assertion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assertion_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    subject_entity_id UUID NOT NULL,
    predicate VARCHAR(100),
    object_value VARCHAR(500),
    object_entity_id UUID,
    source_system_id UUID NOT NULL,
    source_object_id UUID,
    asserted_on TIMESTAMPTZ NOT NULL,
    prior_assertion_id UUID,
    knowledge_id UUID,
    assertion_type assertiontype_t NOT NULL,
    relationship_type_id UUID
);

-- ========== Institutional Relationship ==========
CREATE TABLE institutional_relationships (
    institutional_relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    institutional_relationship_name VARCHAR(200) NOT NULL,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    relationship_type_id UUID NOT NULL,
    from_entity_id UUID NOT NULL,
    to_entity_id UUID NOT NULL,
    superseded_by_id UUID
);

-- ========== Knowledge ==========
CREATE TABLE knowledges (
    knowledge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Reason ==========
CREATE TABLE reasons (
    reason_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reason_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    reason_graph_id UUID NOT NULL,
    derived_from_reason_id UUID
);

-- ========== Reason Graph ==========
CREATE TABLE reason_graphs (
    reason_graph_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reason_graph_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Decision Objective ==========
CREATE TABLE decision_objectives (
    decision_objective_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_objective_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Occasion ==========
CREATE TABLE occasions (
    occasion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occasion_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    decision_objective_id UUID NOT NULL,
    pattern_of_relevance_id UUID NOT NULL,
    context_id UUID NOT NULL,
    occasion_status occasionlifecycle_t NOT NULL
);

-- ========== Pattern of Relevance ==========
CREATE TABLE pattern_of_relevances (
    pattern_of_relevance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_of_relevance_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Decision ==========
CREATE TABLE decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    reason_graph_id UUID NOT NULL,
    decision_state_id UUID NOT NULL,
    accountable_owner_id UUID NOT NULL,
    institutional_act_id UUID
);

-- ========== Decision State ==========
CREATE TABLE decision_states (
    decision_state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_state_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    state_value decisionstatestatus_t NOT NULL
);

-- ========== Institutional Action ==========
CREATE TABLE institutional_actions (
    institutional_action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institutional_action_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    institutional_act_id UUID NOT NULL
);

-- ========== Outcome ==========
CREATE TABLE outcomes (
    outcome_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    institutional_action_id UUID NOT NULL
);

-- ========== Experience ==========
CREATE TABLE experiences (
    experience_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experience_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    outcome_id UUID NOT NULL,
    context_id UUID NOT NULL
);

-- ========== Governance ==========
CREATE TABLE governances (
    governance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    governance_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Accountable Owner ==========
CREATE TABLE accountable_owners (
    accountable_owner_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    accountable_owner_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Source System ==========
CREATE TABLE source_systems (
    source_system_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    source_system_name VARCHAR(200) NOT NULL,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Source Object ==========
CREATE TABLE source_objects (
    source_object_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    source_object_name VARCHAR(200) NOT NULL,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    source_system_id UUID NOT NULL
);

-- ========== Institutional Act ==========
CREATE TABLE institutional_acts (
    institutional_act_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institutional_act_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID,
    governance_id UUID NOT NULL,
    accountable_owner_id UUID NOT NULL,
    decision_id UUID,
    superseded_act_id UUID
);

-- ========== Context ==========
CREATE TABLE contexts (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_name VARCHAR(200) NOT NULL UNIQUE,
    lifecycle_state lifecyclestate_t NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    governance_status governancestatus_t NOT NULL,
    created_by UUID NOT NULL,
    created_on TIMESTAMPTZ NOT NULL,
    modified_by UUID,
    modified_on TIMESTAMPTZ,
    version_number INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID
);

-- ========== Join tables (M:N relationships) ==========
CREATE TABLE reason_decision_objectives (
    reason_id UUID NOT NULL REFERENCES reasons(reason_id),
    decision_objective_id UUID NOT NULL REFERENCES decision_objectives(decision_objective_id),
    PRIMARY KEY (reason_id, decision_objective_id)
);

CREATE TABLE reason_evidence (
    reason_id UUID NOT NULL REFERENCES reasons(reason_id),
    evidence_id UUID NOT NULL REFERENCES evidences(evidence_id),
    PRIMARY KEY (reason_id, evidence_id)
);

CREATE TABLE assertion_evidence (
    assertion_id UUID NOT NULL REFERENCES assertions(assertion_id),
    evidence_id UUID NOT NULL REFERENCES evidences(evidence_id),
    PRIMARY KEY (assertion_id, evidence_id)
);

CREATE TABLE institutional_relationship_assertions (
    institutional_relationship_id UUID NOT NULL REFERENCES institutional_relationships(institutional_relationship_id),
    assertion_id UUID NOT NULL REFERENCES assertions(assertion_id),
    PRIMARY KEY (institutional_relationship_id, assertion_id)
);
-- ---------- Foreign key constraints ----------
ALTER TABLE enterprises ADD CONSTRAINT fk_enterprises_enterprise_type_id FOREIGN KEY (enterprise_type_id) REFERENCES enterprise_types(enterprise_type_id);
ALTER TABLE enterprises ADD CONSTRAINT fk_enterprises_country_id FOREIGN KEY (country_id) REFERENCES countries(country_id);
ALTER TABLE enterprises ADD CONSTRAINT fk_enterprises_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE enterprises ADD CONSTRAINT fk_enterprises_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE enterprises ADD CONSTRAINT fk_enterprises_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES enterprises(enterprise_id);
ALTER TABLE business_domains ADD CONSTRAINT fk_business_domains_enterprise_id FOREIGN KEY (enterprise_id) REFERENCES enterprises(enterprise_id);
ALTER TABLE business_domains ADD CONSTRAINT fk_business_domains_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE business_domains ADD CONSTRAINT fk_business_domains_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE business_domains ADD CONSTRAINT fk_business_domains_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES business_domains(business_domain_id);
ALTER TABLE institutional_concepts ADD CONSTRAINT fk_institutional_concepts_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_concepts ADD CONSTRAINT fk_institutional_concepts_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_concepts ADD CONSTRAINT fk_institutional_concepts_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES institutional_concepts(institutional_concept_id);
ALTER TABLE institutional_concepts ADD CONSTRAINT fk_institutional_concepts_enterprise_id FOREIGN KEY (enterprise_id) REFERENCES enterprises(enterprise_id);
ALTER TABLE relationship_types ADD CONSTRAINT fk_relationship_types_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE relationship_types ADD CONSTRAINT fk_relationship_types_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE relationship_types ADD CONSTRAINT fk_relationship_types_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES relationship_types(relationship_type_id);
ALTER TABLE entity_types ADD CONSTRAINT fk_entity_types_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE entity_types ADD CONSTRAINT fk_entity_types_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE entity_types ADD CONSTRAINT fk_entity_types_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES entity_types(entity_type_id);
ALTER TABLE entity_types ADD CONSTRAINT fk_entity_types_institutional_concept_id FOREIGN KEY (institutional_concept_id) REFERENCES institutional_concepts(institutional_concept_id);
ALTER TABLE enterprise_entities ADD CONSTRAINT fk_enterprise_entities_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE enterprise_entities ADD CONSTRAINT fk_enterprise_entities_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE enterprise_entities ADD CONSTRAINT fk_enterprise_entities_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE enterprise_entities ADD CONSTRAINT fk_enterprise_entities_entity_type_id FOREIGN KEY (entity_type_id) REFERENCES entity_types(entity_type_id);
ALTER TABLE enterprise_entities ADD CONSTRAINT fk_enterprise_entities_business_domain_id FOREIGN KEY (business_domain_id) REFERENCES business_domains(business_domain_id);
ALTER TABLE evidences ADD CONSTRAINT fk_evidences_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE evidences ADD CONSTRAINT fk_evidences_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE evidences ADD CONSTRAINT fk_evidences_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES evidences(evidence_id);
ALTER TABLE evidences ADD CONSTRAINT fk_evidences_source_object_id FOREIGN KEY (source_object_id) REFERENCES source_objects(source_object_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES assertions(assertion_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_subject_entity_id FOREIGN KEY (subject_entity_id) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_object_entity_id FOREIGN KEY (object_entity_id) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_source_system_id FOREIGN KEY (source_system_id) REFERENCES source_systems(source_system_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_source_object_id FOREIGN KEY (source_object_id) REFERENCES source_objects(source_object_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_prior_assertion_id FOREIGN KEY (prior_assertion_id) REFERENCES assertions(assertion_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_knowledge_id FOREIGN KEY (knowledge_id) REFERENCES knowledges(knowledge_id);
ALTER TABLE assertions ADD CONSTRAINT fk_assertions_relationship_type_id FOREIGN KEY (relationship_type_id) REFERENCES relationship_types(relationship_type_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES institutional_relationships(institutional_relationship_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_relationship_type_id FOREIGN KEY (relationship_type_id) REFERENCES relationship_types(relationship_type_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_from_entity_id FOREIGN KEY (tenant_id,from_entity_id) REFERENCES enterprise_entities(tenant_id,enterprise_entity_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_to_entity_id FOREIGN KEY (tenant_id,to_entity_id) REFERENCES enterprise_entities(tenant_id,enterprise_entity_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_superseded_by_id FOREIGN KEY (superseded_by_id) REFERENCES institutional_relationships(institutional_relationship_id);
ALTER TABLE knowledges ADD CONSTRAINT fk_knowledges_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE knowledges ADD CONSTRAINT fk_knowledges_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE knowledges ADD CONSTRAINT fk_knowledges_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES knowledges(knowledge_id);
ALTER TABLE reasons ADD CONSTRAINT fk_reasons_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE reasons ADD CONSTRAINT fk_reasons_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE reasons ADD CONSTRAINT fk_reasons_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES reasons(reason_id);
ALTER TABLE reasons ADD CONSTRAINT fk_reasons_reason_graph_id FOREIGN KEY (reason_graph_id) REFERENCES reason_graphs(reason_graph_id);
ALTER TABLE reasons ADD CONSTRAINT fk_reasons_derived_from_reason_id FOREIGN KEY (derived_from_reason_id) REFERENCES reasons(reason_id);
ALTER TABLE reason_graphs ADD CONSTRAINT fk_reason_graphs_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE reason_graphs ADD CONSTRAINT fk_reason_graphs_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE reason_graphs ADD CONSTRAINT fk_reason_graphs_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES reason_graphs(reason_graph_id);
ALTER TABLE decision_objectives ADD CONSTRAINT fk_decision_objectives_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE decision_objectives ADD CONSTRAINT fk_decision_objectives_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE decision_objectives ADD CONSTRAINT fk_decision_objectives_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES decision_objectives(decision_objective_id);
ALTER TABLE occasions ADD CONSTRAINT fk_occasions_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE occasions ADD CONSTRAINT fk_occasions_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE occasions ADD CONSTRAINT fk_occasions_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES occasions(occasion_id);
ALTER TABLE occasions ADD CONSTRAINT fk_occasions_decision_objective_id FOREIGN KEY (decision_objective_id) REFERENCES decision_objectives(decision_objective_id);
ALTER TABLE occasions ADD CONSTRAINT fk_occasions_pattern_of_relevance_id FOREIGN KEY (pattern_of_relevance_id) REFERENCES pattern_of_relevances(pattern_of_relevance_id);
ALTER TABLE occasions ADD CONSTRAINT fk_occasions_context_id FOREIGN KEY (context_id) REFERENCES contexts(context_id);
ALTER TABLE pattern_of_relevances ADD CONSTRAINT fk_pattern_of_relevances_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE pattern_of_relevances ADD CONSTRAINT fk_pattern_of_relevances_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE pattern_of_relevances ADD CONSTRAINT fk_pattern_of_relevances_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES pattern_of_relevances(pattern_of_relevance_id);
ALTER TABLE decisions ADD CONSTRAINT fk_decisions_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE decisions ADD CONSTRAINT fk_decisions_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE decisions ADD CONSTRAINT fk_decisions_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES decisions(decision_id);
ALTER TABLE decisions ADD CONSTRAINT fk_decisions_reason_graph_id FOREIGN KEY (reason_graph_id) REFERENCES reason_graphs(reason_graph_id);
ALTER TABLE decisions ADD CONSTRAINT fk_decisions_decision_state_id FOREIGN KEY (decision_state_id) REFERENCES decision_states(decision_state_id);
ALTER TABLE decisions ADD CONSTRAINT fk_decisions_accountable_owner_id FOREIGN KEY (accountable_owner_id) REFERENCES accountable_owners(accountable_owner_id);
ALTER TABLE decisions ADD CONSTRAINT fk_decisions_institutional_act_id FOREIGN KEY (institutional_act_id) REFERENCES institutional_acts(institutional_act_id);
ALTER TABLE decision_states ADD CONSTRAINT fk_decision_states_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE decision_states ADD CONSTRAINT fk_decision_states_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE decision_states ADD CONSTRAINT fk_decision_states_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES decision_states(decision_state_id);
ALTER TABLE institutional_actions ADD CONSTRAINT fk_institutional_actions_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_actions ADD CONSTRAINT fk_institutional_actions_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_actions ADD CONSTRAINT fk_institutional_actions_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES institutional_actions(institutional_action_id);
ALTER TABLE institutional_actions ADD CONSTRAINT fk_institutional_actions_institutional_act_id FOREIGN KEY (institutional_act_id) REFERENCES institutional_acts(institutional_act_id);
ALTER TABLE outcomes ADD CONSTRAINT fk_outcomes_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE outcomes ADD CONSTRAINT fk_outcomes_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE outcomes ADD CONSTRAINT fk_outcomes_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES outcomes(outcome_id);
ALTER TABLE outcomes ADD CONSTRAINT fk_outcomes_institutional_action_id FOREIGN KEY (institutional_action_id) REFERENCES institutional_actions(institutional_action_id);
ALTER TABLE experiences ADD CONSTRAINT fk_experiences_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE experiences ADD CONSTRAINT fk_experiences_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE experiences ADD CONSTRAINT fk_experiences_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES experiences(experience_id);
ALTER TABLE experiences ADD CONSTRAINT fk_experiences_outcome_id FOREIGN KEY (outcome_id) REFERENCES outcomes(outcome_id);
ALTER TABLE experiences ADD CONSTRAINT fk_experiences_context_id FOREIGN KEY (context_id) REFERENCES contexts(context_id);
ALTER TABLE governances ADD CONSTRAINT fk_governances_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE governances ADD CONSTRAINT fk_governances_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE governances ADD CONSTRAINT fk_governances_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES governances(governance_id);
ALTER TABLE accountable_owners ADD CONSTRAINT fk_accountable_owners_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE accountable_owners ADD CONSTRAINT fk_accountable_owners_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE accountable_owners ADD CONSTRAINT fk_accountable_owners_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES accountable_owners(accountable_owner_id);
ALTER TABLE source_systems ADD CONSTRAINT fk_source_systems_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE source_systems ADD CONSTRAINT fk_source_systems_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE source_systems ADD CONSTRAINT fk_source_systems_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES source_systems(source_system_id);
ALTER TABLE source_objects ADD CONSTRAINT fk_source_objects_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE source_objects ADD CONSTRAINT fk_source_objects_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE source_objects ADD CONSTRAINT fk_source_objects_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES source_objects(source_object_id);
ALTER TABLE source_objects ADD CONSTRAINT fk_source_objects_source_system_id FOREIGN KEY (tenant_id,source_system_id) REFERENCES source_systems(tenant_id,source_system_id);
ALTER TABLE institutional_acts ADD CONSTRAINT fk_institutional_acts_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_acts ADD CONSTRAINT fk_institutional_acts_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE institutional_acts ADD CONSTRAINT fk_institutional_acts_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES institutional_acts(institutional_act_id);
ALTER TABLE institutional_acts ADD CONSTRAINT fk_institutional_acts_governance_id FOREIGN KEY (governance_id) REFERENCES governances(governance_id);
ALTER TABLE institutional_acts ADD CONSTRAINT fk_institutional_acts_accountable_owner_id FOREIGN KEY (accountable_owner_id) REFERENCES accountable_owners(accountable_owner_id);
ALTER TABLE institutional_acts ADD CONSTRAINT fk_institutional_acts_decision_id FOREIGN KEY (decision_id) REFERENCES decisions(decision_id);
ALTER TABLE institutional_acts ADD CONSTRAINT fk_institutional_acts_superseded_act_id FOREIGN KEY (superseded_act_id) REFERENCES institutional_acts(institutional_act_id);
ALTER TABLE contexts ADD CONSTRAINT fk_contexts_created_by FOREIGN KEY (created_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE contexts ADD CONSTRAINT fk_contexts_modified_by FOREIGN KEY (modified_by) REFERENCES enterprise_entities(enterprise_entity_id);
ALTER TABLE contexts ADD CONSTRAINT fk_contexts_previous_version_id FOREIGN KEY (previous_version_id) REFERENCES contexts(context_id);

-- ---------- Composite uniqueness constraints ----------
ALTER TABLE business_domains ADD CONSTRAINT uq_business_domains_enterprise_id_domain_name UNIQUE (enterprise_id,domain_name);
ALTER TABLE enterprise_entities ADD CONSTRAINT uq_enterprise_entities_tenant_name UNIQUE (tenant_id,enterprise_entity_name);
ALTER TABLE enterprise_entities ADD CONSTRAINT uq_enterprise_entities_tenant_pk UNIQUE (tenant_id,enterprise_entity_id);
ALTER TABLE source_systems ADD CONSTRAINT uq_source_systems_tenant_name UNIQUE (tenant_id,source_system_name);
ALTER TABLE source_systems ADD CONSTRAINT uq_source_systems_tenant_pk UNIQUE (tenant_id,source_system_id);
ALTER TABLE source_objects ADD CONSTRAINT uq_source_objects_tenant_name UNIQUE (tenant_id,source_object_name);
ALTER TABLE source_objects ADD CONSTRAINT uq_source_objects_tenant_pk UNIQUE (tenant_id,source_object_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT uq_institutional_relationships_tenant_name UNIQUE (tenant_id,institutional_relationship_name);
ALTER TABLE institutional_relationships ADD CONSTRAINT uq_institutional_relationships_tenant_pk UNIQUE (tenant_id,institutional_relationship_id);

-- ---------- CHECK constraints ----------
-- Enforces the split from point A: an Assertion is either relational (governed
-- verb + Entity object) or literal (attribute name + value), never a mix of both
-- and never neither.
ALTER TABLE assertions ADD CONSTRAINT chk_assertions_relational_xor_literal CHECK (
    (relationship_type_id IS NOT NULL AND object_entity_id IS NOT NULL AND predicate IS NULL AND object_value IS NULL)
    OR
    (relationship_type_id IS NULL AND object_entity_id IS NULL AND predicate IS NOT NULL)
);

-- ---------- Indexes ----------
CREATE INDEX idx_enterprise_entities_tenant_id ON enterprise_entities(tenant_id);
CREATE INDEX idx_source_systems_tenant_id ON source_systems(tenant_id);
CREATE INDEX idx_source_objects_tenant_id ON source_objects(tenant_id);
CREATE INDEX idx_institutional_relationships_tenant_id ON institutional_relationships(tenant_id);
CREATE INDEX idx_enterprises_enterprise_name ON enterprises(enterprise_name);
CREATE INDEX idx_enterprises_enterprise_type_id ON enterprises(enterprise_type_id);
CREATE INDEX idx_enterprises_country_id ON enterprises(country_id);
CREATE INDEX idx_enterprises_lifecycle_state ON enterprises(lifecycle_state);
CREATE INDEX idx_enterprises_effective_from ON enterprises(effective_from);
CREATE INDEX idx_enterprises_effective_to ON enterprises(effective_to);
CREATE INDEX idx_enterprises_governance_status ON enterprises(governance_status);
CREATE INDEX idx_enterprises_created_by ON enterprises(created_by);
CREATE INDEX idx_enterprises_created_on ON enterprises(created_on);
CREATE INDEX idx_enterprises_modified_by ON enterprises(modified_by);
CREATE INDEX idx_enterprises_modified_on ON enterprises(modified_on);
CREATE INDEX idx_enterprises_version_number ON enterprises(version_number);
CREATE INDEX idx_enterprises_previous_version_id ON enterprises(previous_version_id);
CREATE INDEX idx_enterprise_types_type_name ON enterprise_types(type_name);
CREATE INDEX idx_countries_country_name ON countries(country_name);
CREATE INDEX idx_countries_iso2_code ON countries(iso2_code);
CREATE INDEX idx_countries_iso3_code ON countries(iso3_code);
CREATE INDEX idx_business_domains_enterprise_id ON business_domains(enterprise_id);
CREATE INDEX idx_business_domains_domain_name ON business_domains(domain_name);
CREATE INDEX idx_business_domains_lifecycle_state ON business_domains(lifecycle_state);
CREATE INDEX idx_business_domains_effective_from ON business_domains(effective_from);
CREATE INDEX idx_business_domains_effective_to ON business_domains(effective_to);
CREATE INDEX idx_business_domains_governance_status ON business_domains(governance_status);
CREATE INDEX idx_business_domains_created_by ON business_domains(created_by);
CREATE INDEX idx_business_domains_created_on ON business_domains(created_on);
CREATE INDEX idx_business_domains_modified_by ON business_domains(modified_by);
CREATE INDEX idx_business_domains_modified_on ON business_domains(modified_on);
CREATE INDEX idx_business_domains_version_number ON business_domains(version_number);
CREATE INDEX idx_business_domains_previous_version_id ON business_domains(previous_version_id);
CREATE INDEX idx_institutional_concepts_institutional_concept_name ON institutional_concepts(institutional_concept_name);
CREATE INDEX idx_institutional_concepts_lifecycle_state ON institutional_concepts(lifecycle_state);
CREATE INDEX idx_institutional_concepts_effective_from ON institutional_concepts(effective_from);
CREATE INDEX idx_institutional_concepts_effective_to ON institutional_concepts(effective_to);
CREATE INDEX idx_institutional_concepts_governance_status ON institutional_concepts(governance_status);
CREATE INDEX idx_institutional_concepts_created_by ON institutional_concepts(created_by);
CREATE INDEX idx_institutional_concepts_created_on ON institutional_concepts(created_on);
CREATE INDEX idx_institutional_concepts_modified_by ON institutional_concepts(modified_by);
CREATE INDEX idx_institutional_concepts_modified_on ON institutional_concepts(modified_on);
CREATE INDEX idx_institutional_concepts_version_number ON institutional_concepts(version_number);
CREATE INDEX idx_institutional_concepts_previous_version_id ON institutional_concepts(previous_version_id);
CREATE INDEX idx_institutional_concepts_enterprise_id ON institutional_concepts(enterprise_id);
CREATE INDEX idx_relationship_types_relationship_type_name ON relationship_types(relationship_type_name);
CREATE INDEX idx_relationship_types_lifecycle_state ON relationship_types(lifecycle_state);
CREATE INDEX idx_relationship_types_effective_from ON relationship_types(effective_from);
CREATE INDEX idx_relationship_types_effective_to ON relationship_types(effective_to);
CREATE INDEX idx_relationship_types_governance_status ON relationship_types(governance_status);
CREATE INDEX idx_relationship_types_created_by ON relationship_types(created_by);
CREATE INDEX idx_relationship_types_created_on ON relationship_types(created_on);
CREATE INDEX idx_relationship_types_modified_by ON relationship_types(modified_by);
CREATE INDEX idx_relationship_types_modified_on ON relationship_types(modified_on);
CREATE INDEX idx_relationship_types_version_number ON relationship_types(version_number);
CREATE INDEX idx_relationship_types_previous_version_id ON relationship_types(previous_version_id);
CREATE INDEX idx_entity_types_entity_type_name ON entity_types(entity_type_name);
CREATE INDEX idx_entity_types_lifecycle_state ON entity_types(lifecycle_state);
CREATE INDEX idx_entity_types_effective_from ON entity_types(effective_from);
CREATE INDEX idx_entity_types_effective_to ON entity_types(effective_to);
CREATE INDEX idx_entity_types_governance_status ON entity_types(governance_status);
CREATE INDEX idx_entity_types_created_by ON entity_types(created_by);
CREATE INDEX idx_entity_types_created_on ON entity_types(created_on);
CREATE INDEX idx_entity_types_modified_by ON entity_types(modified_by);
CREATE INDEX idx_entity_types_modified_on ON entity_types(modified_on);
CREATE INDEX idx_entity_types_version_number ON entity_types(version_number);
CREATE INDEX idx_entity_types_previous_version_id ON entity_types(previous_version_id);
CREATE INDEX idx_entity_types_institutional_concept_id ON entity_types(institutional_concept_id);
CREATE INDEX idx_enterprise_entities_enterprise_entity_name ON enterprise_entities(enterprise_entity_name);
CREATE INDEX idx_enterprise_entities_lifecycle_state ON enterprise_entities(lifecycle_state);
CREATE INDEX idx_enterprise_entities_effective_from ON enterprise_entities(effective_from);
CREATE INDEX idx_enterprise_entities_effective_to ON enterprise_entities(effective_to);
CREATE INDEX idx_enterprise_entities_governance_status ON enterprise_entities(governance_status);
CREATE INDEX idx_enterprise_entities_created_by ON enterprise_entities(created_by);
CREATE INDEX idx_enterprise_entities_created_on ON enterprise_entities(created_on);
CREATE INDEX idx_enterprise_entities_modified_by ON enterprise_entities(modified_by);
CREATE INDEX idx_enterprise_entities_modified_on ON enterprise_entities(modified_on);
CREATE INDEX idx_enterprise_entities_version_number ON enterprise_entities(version_number);
CREATE INDEX idx_enterprise_entities_previous_version_id ON enterprise_entities(previous_version_id);
CREATE INDEX idx_enterprise_entities_entity_type_id ON enterprise_entities(entity_type_id);
CREATE INDEX idx_enterprise_entities_business_domain_id ON enterprise_entities(business_domain_id);
CREATE INDEX idx_evidences_evidence_name ON evidences(evidence_name);
CREATE INDEX idx_evidences_lifecycle_state ON evidences(lifecycle_state);
CREATE INDEX idx_evidences_effective_from ON evidences(effective_from);
CREATE INDEX idx_evidences_effective_to ON evidences(effective_to);
CREATE INDEX idx_evidences_governance_status ON evidences(governance_status);
CREATE INDEX idx_evidences_created_by ON evidences(created_by);
CREATE INDEX idx_evidences_created_on ON evidences(created_on);
CREATE INDEX idx_evidences_modified_by ON evidences(modified_by);
CREATE INDEX idx_evidences_modified_on ON evidences(modified_on);
CREATE INDEX idx_evidences_version_number ON evidences(version_number);
CREATE INDEX idx_evidences_previous_version_id ON evidences(previous_version_id);
CREATE INDEX idx_evidences_source_object_id ON evidences(source_object_id);
CREATE INDEX idx_assertions_assertion_name ON assertions(assertion_name);
CREATE INDEX idx_assertions_lifecycle_state ON assertions(lifecycle_state);
CREATE INDEX idx_assertions_effective_from ON assertions(effective_from);
CREATE INDEX idx_assertions_effective_to ON assertions(effective_to);
CREATE INDEX idx_assertions_governance_status ON assertions(governance_status);
CREATE INDEX idx_assertions_created_by ON assertions(created_by);
CREATE INDEX idx_assertions_created_on ON assertions(created_on);
CREATE INDEX idx_assertions_modified_by ON assertions(modified_by);
CREATE INDEX idx_assertions_modified_on ON assertions(modified_on);
CREATE INDEX idx_assertions_version_number ON assertions(version_number);
CREATE INDEX idx_assertions_previous_version_id ON assertions(previous_version_id);
CREATE INDEX idx_assertions_subject_entity_id ON assertions(subject_entity_id);
CREATE INDEX idx_assertions_predicate ON assertions(predicate);
CREATE INDEX idx_assertions_object_value ON assertions(object_value);
CREATE INDEX idx_assertions_object_entity_id ON assertions(object_entity_id);
CREATE INDEX idx_assertions_source_system_id ON assertions(source_system_id);
CREATE INDEX idx_assertions_source_object_id ON assertions(source_object_id);
CREATE INDEX idx_assertions_asserted_on ON assertions(asserted_on);
CREATE INDEX idx_assertions_prior_assertion_id ON assertions(prior_assertion_id);
CREATE INDEX idx_assertions_knowledge_id ON assertions(knowledge_id);
CREATE INDEX idx_assertions_assertion_type ON assertions(assertion_type);
CREATE INDEX idx_assertions_relationship_type_id ON assertions(relationship_type_id);
CREATE INDEX idx_institutional_relationships_institutional_relationship_name ON institutional_relationships(institutional_relationship_name);
CREATE INDEX idx_institutional_relationships_lifecycle_state ON institutional_relationships(lifecycle_state);
CREATE INDEX idx_institutional_relationships_effective_from ON institutional_relationships(effective_from);
CREATE INDEX idx_institutional_relationships_effective_to ON institutional_relationships(effective_to);
CREATE INDEX idx_institutional_relationships_governance_status ON institutional_relationships(governance_status);
CREATE INDEX idx_institutional_relationships_created_by ON institutional_relationships(created_by);
CREATE INDEX idx_institutional_relationships_created_on ON institutional_relationships(created_on);
CREATE INDEX idx_institutional_relationships_modified_by ON institutional_relationships(modified_by);
CREATE INDEX idx_institutional_relationships_modified_on ON institutional_relationships(modified_on);
CREATE INDEX idx_institutional_relationships_version_number ON institutional_relationships(version_number);
CREATE INDEX idx_institutional_relationships_previous_version_id ON institutional_relationships(previous_version_id);
CREATE INDEX idx_institutional_relationships_relationship_type_id ON institutional_relationships(relationship_type_id);
CREATE INDEX idx_institutional_relationships_from_entity_id ON institutional_relationships(from_entity_id);
CREATE INDEX idx_institutional_relationships_to_entity_id ON institutional_relationships(to_entity_id);
CREATE INDEX idx_institutional_relationships_superseded_by_id ON institutional_relationships(superseded_by_id);
CREATE INDEX idx_knowledges_knowledge_name ON knowledges(knowledge_name);
CREATE INDEX idx_knowledges_lifecycle_state ON knowledges(lifecycle_state);
CREATE INDEX idx_knowledges_effective_from ON knowledges(effective_from);
CREATE INDEX idx_knowledges_effective_to ON knowledges(effective_to);
CREATE INDEX idx_knowledges_governance_status ON knowledges(governance_status);
CREATE INDEX idx_knowledges_created_by ON knowledges(created_by);
CREATE INDEX idx_knowledges_created_on ON knowledges(created_on);
CREATE INDEX idx_knowledges_modified_by ON knowledges(modified_by);
CREATE INDEX idx_knowledges_modified_on ON knowledges(modified_on);
CREATE INDEX idx_knowledges_version_number ON knowledges(version_number);
CREATE INDEX idx_knowledges_previous_version_id ON knowledges(previous_version_id);
CREATE INDEX idx_reasons_reason_name ON reasons(reason_name);
CREATE INDEX idx_reasons_lifecycle_state ON reasons(lifecycle_state);
CREATE INDEX idx_reasons_effective_from ON reasons(effective_from);
CREATE INDEX idx_reasons_effective_to ON reasons(effective_to);
CREATE INDEX idx_reasons_governance_status ON reasons(governance_status);
CREATE INDEX idx_reasons_created_by ON reasons(created_by);
CREATE INDEX idx_reasons_created_on ON reasons(created_on);
CREATE INDEX idx_reasons_modified_by ON reasons(modified_by);
CREATE INDEX idx_reasons_modified_on ON reasons(modified_on);
CREATE INDEX idx_reasons_version_number ON reasons(version_number);
CREATE INDEX idx_reasons_previous_version_id ON reasons(previous_version_id);
CREATE INDEX idx_reasons_reason_graph_id ON reasons(reason_graph_id);
CREATE INDEX idx_reasons_derived_from_reason_id ON reasons(derived_from_reason_id);
CREATE INDEX idx_reason_graphs_reason_graph_name ON reason_graphs(reason_graph_name);
CREATE INDEX idx_reason_graphs_lifecycle_state ON reason_graphs(lifecycle_state);
CREATE INDEX idx_reason_graphs_effective_from ON reason_graphs(effective_from);
CREATE INDEX idx_reason_graphs_effective_to ON reason_graphs(effective_to);
CREATE INDEX idx_reason_graphs_governance_status ON reason_graphs(governance_status);
CREATE INDEX idx_reason_graphs_created_by ON reason_graphs(created_by);
CREATE INDEX idx_reason_graphs_created_on ON reason_graphs(created_on);
CREATE INDEX idx_reason_graphs_modified_by ON reason_graphs(modified_by);
CREATE INDEX idx_reason_graphs_modified_on ON reason_graphs(modified_on);
CREATE INDEX idx_reason_graphs_version_number ON reason_graphs(version_number);
CREATE INDEX idx_reason_graphs_previous_version_id ON reason_graphs(previous_version_id);
CREATE INDEX idx_decision_objectives_decision_objective_name ON decision_objectives(decision_objective_name);
CREATE INDEX idx_decision_objectives_lifecycle_state ON decision_objectives(lifecycle_state);
CREATE INDEX idx_decision_objectives_effective_from ON decision_objectives(effective_from);
CREATE INDEX idx_decision_objectives_effective_to ON decision_objectives(effective_to);
CREATE INDEX idx_decision_objectives_governance_status ON decision_objectives(governance_status);
CREATE INDEX idx_decision_objectives_created_by ON decision_objectives(created_by);
CREATE INDEX idx_decision_objectives_created_on ON decision_objectives(created_on);
CREATE INDEX idx_decision_objectives_modified_by ON decision_objectives(modified_by);
CREATE INDEX idx_decision_objectives_modified_on ON decision_objectives(modified_on);
CREATE INDEX idx_decision_objectives_version_number ON decision_objectives(version_number);
CREATE INDEX idx_decision_objectives_previous_version_id ON decision_objectives(previous_version_id);
CREATE INDEX idx_occasions_occasion_name ON occasions(occasion_name);
CREATE INDEX idx_occasions_lifecycle_state ON occasions(lifecycle_state);
CREATE INDEX idx_occasions_effective_from ON occasions(effective_from);
CREATE INDEX idx_occasions_effective_to ON occasions(effective_to);
CREATE INDEX idx_occasions_governance_status ON occasions(governance_status);
CREATE INDEX idx_occasions_created_by ON occasions(created_by);
CREATE INDEX idx_occasions_created_on ON occasions(created_on);
CREATE INDEX idx_occasions_modified_by ON occasions(modified_by);
CREATE INDEX idx_occasions_modified_on ON occasions(modified_on);
CREATE INDEX idx_occasions_version_number ON occasions(version_number);
CREATE INDEX idx_occasions_previous_version_id ON occasions(previous_version_id);
CREATE INDEX idx_occasions_decision_objective_id ON occasions(decision_objective_id);
CREATE INDEX idx_occasions_pattern_of_relevance_id ON occasions(pattern_of_relevance_id);
CREATE INDEX idx_occasions_context_id ON occasions(context_id);
CREATE INDEX idx_occasions_occasion_status ON occasions(occasion_status);
CREATE INDEX idx_pattern_of_relevances_pattern_of_relevance_name ON pattern_of_relevances(pattern_of_relevance_name);
CREATE INDEX idx_pattern_of_relevances_lifecycle_state ON pattern_of_relevances(lifecycle_state);
CREATE INDEX idx_pattern_of_relevances_effective_from ON pattern_of_relevances(effective_from);
CREATE INDEX idx_pattern_of_relevances_effective_to ON pattern_of_relevances(effective_to);
CREATE INDEX idx_pattern_of_relevances_governance_status ON pattern_of_relevances(governance_status);
CREATE INDEX idx_pattern_of_relevances_created_by ON pattern_of_relevances(created_by);
CREATE INDEX idx_pattern_of_relevances_created_on ON pattern_of_relevances(created_on);
CREATE INDEX idx_pattern_of_relevances_modified_by ON pattern_of_relevances(modified_by);
CREATE INDEX idx_pattern_of_relevances_modified_on ON pattern_of_relevances(modified_on);
CREATE INDEX idx_pattern_of_relevances_version_number ON pattern_of_relevances(version_number);
CREATE INDEX idx_pattern_of_relevances_previous_version_id ON pattern_of_relevances(previous_version_id);
CREATE INDEX idx_decisions_decision_name ON decisions(decision_name);
CREATE INDEX idx_decisions_lifecycle_state ON decisions(lifecycle_state);
CREATE INDEX idx_decisions_effective_from ON decisions(effective_from);
CREATE INDEX idx_decisions_effective_to ON decisions(effective_to);
CREATE INDEX idx_decisions_governance_status ON decisions(governance_status);
CREATE INDEX idx_decisions_created_by ON decisions(created_by);
CREATE INDEX idx_decisions_created_on ON decisions(created_on);
CREATE INDEX idx_decisions_modified_by ON decisions(modified_by);
CREATE INDEX idx_decisions_modified_on ON decisions(modified_on);
CREATE INDEX idx_decisions_version_number ON decisions(version_number);
CREATE INDEX idx_decisions_previous_version_id ON decisions(previous_version_id);
CREATE INDEX idx_decisions_reason_graph_id ON decisions(reason_graph_id);
CREATE INDEX idx_decisions_decision_state_id ON decisions(decision_state_id);
CREATE INDEX idx_decisions_accountable_owner_id ON decisions(accountable_owner_id);
CREATE INDEX idx_decisions_institutional_act_id ON decisions(institutional_act_id);
CREATE INDEX idx_decision_states_decision_state_name ON decision_states(decision_state_name);
CREATE INDEX idx_decision_states_lifecycle_state ON decision_states(lifecycle_state);
CREATE INDEX idx_decision_states_effective_from ON decision_states(effective_from);
CREATE INDEX idx_decision_states_effective_to ON decision_states(effective_to);
CREATE INDEX idx_decision_states_governance_status ON decision_states(governance_status);
CREATE INDEX idx_decision_states_created_by ON decision_states(created_by);
CREATE INDEX idx_decision_states_created_on ON decision_states(created_on);
CREATE INDEX idx_decision_states_modified_by ON decision_states(modified_by);
CREATE INDEX idx_decision_states_modified_on ON decision_states(modified_on);
CREATE INDEX idx_decision_states_version_number ON decision_states(version_number);
CREATE INDEX idx_decision_states_previous_version_id ON decision_states(previous_version_id);
CREATE INDEX idx_decision_states_state_value ON decision_states(state_value);
CREATE INDEX idx_institutional_actions_institutional_action_name ON institutional_actions(institutional_action_name);
CREATE INDEX idx_institutional_actions_lifecycle_state ON institutional_actions(lifecycle_state);
CREATE INDEX idx_institutional_actions_effective_from ON institutional_actions(effective_from);
CREATE INDEX idx_institutional_actions_effective_to ON institutional_actions(effective_to);
CREATE INDEX idx_institutional_actions_governance_status ON institutional_actions(governance_status);
CREATE INDEX idx_institutional_actions_created_by ON institutional_actions(created_by);
CREATE INDEX idx_institutional_actions_created_on ON institutional_actions(created_on);
CREATE INDEX idx_institutional_actions_modified_by ON institutional_actions(modified_by);
CREATE INDEX idx_institutional_actions_modified_on ON institutional_actions(modified_on);
CREATE INDEX idx_institutional_actions_version_number ON institutional_actions(version_number);
CREATE INDEX idx_institutional_actions_previous_version_id ON institutional_actions(previous_version_id);
CREATE INDEX idx_institutional_actions_institutional_act_id ON institutional_actions(institutional_act_id);
CREATE INDEX idx_outcomes_outcome_name ON outcomes(outcome_name);
CREATE INDEX idx_outcomes_lifecycle_state ON outcomes(lifecycle_state);
CREATE INDEX idx_outcomes_effective_from ON outcomes(effective_from);
CREATE INDEX idx_outcomes_effective_to ON outcomes(effective_to);
CREATE INDEX idx_outcomes_governance_status ON outcomes(governance_status);
CREATE INDEX idx_outcomes_created_by ON outcomes(created_by);
CREATE INDEX idx_outcomes_created_on ON outcomes(created_on);
CREATE INDEX idx_outcomes_modified_by ON outcomes(modified_by);
CREATE INDEX idx_outcomes_modified_on ON outcomes(modified_on);
CREATE INDEX idx_outcomes_version_number ON outcomes(version_number);
CREATE INDEX idx_outcomes_previous_version_id ON outcomes(previous_version_id);
CREATE INDEX idx_outcomes_institutional_action_id ON outcomes(institutional_action_id);
CREATE INDEX idx_experiences_experience_name ON experiences(experience_name);
CREATE INDEX idx_experiences_lifecycle_state ON experiences(lifecycle_state);
CREATE INDEX idx_experiences_effective_from ON experiences(effective_from);
CREATE INDEX idx_experiences_effective_to ON experiences(effective_to);
CREATE INDEX idx_experiences_governance_status ON experiences(governance_status);
CREATE INDEX idx_experiences_created_by ON experiences(created_by);
CREATE INDEX idx_experiences_created_on ON experiences(created_on);
CREATE INDEX idx_experiences_modified_by ON experiences(modified_by);
CREATE INDEX idx_experiences_modified_on ON experiences(modified_on);
CREATE INDEX idx_experiences_version_number ON experiences(version_number);
CREATE INDEX idx_experiences_previous_version_id ON experiences(previous_version_id);
CREATE INDEX idx_experiences_outcome_id ON experiences(outcome_id);
CREATE INDEX idx_experiences_context_id ON experiences(context_id);
CREATE INDEX idx_governances_governance_name ON governances(governance_name);
CREATE INDEX idx_governances_lifecycle_state ON governances(lifecycle_state);
CREATE INDEX idx_governances_effective_from ON governances(effective_from);
CREATE INDEX idx_governances_effective_to ON governances(effective_to);
CREATE INDEX idx_governances_governance_status ON governances(governance_status);
CREATE INDEX idx_governances_created_by ON governances(created_by);
CREATE INDEX idx_governances_created_on ON governances(created_on);
CREATE INDEX idx_governances_modified_by ON governances(modified_by);
CREATE INDEX idx_governances_modified_on ON governances(modified_on);
CREATE INDEX idx_governances_version_number ON governances(version_number);
CREATE INDEX idx_governances_previous_version_id ON governances(previous_version_id);
CREATE INDEX idx_accountable_owners_accountable_owner_name ON accountable_owners(accountable_owner_name);
CREATE INDEX idx_accountable_owners_lifecycle_state ON accountable_owners(lifecycle_state);
CREATE INDEX idx_accountable_owners_effective_from ON accountable_owners(effective_from);
CREATE INDEX idx_accountable_owners_effective_to ON accountable_owners(effective_to);
CREATE INDEX idx_accountable_owners_governance_status ON accountable_owners(governance_status);
CREATE INDEX idx_accountable_owners_created_by ON accountable_owners(created_by);
CREATE INDEX idx_accountable_owners_created_on ON accountable_owners(created_on);
CREATE INDEX idx_accountable_owners_modified_by ON accountable_owners(modified_by);
CREATE INDEX idx_accountable_owners_modified_on ON accountable_owners(modified_on);
CREATE INDEX idx_accountable_owners_version_number ON accountable_owners(version_number);
CREATE INDEX idx_accountable_owners_previous_version_id ON accountable_owners(previous_version_id);
CREATE INDEX idx_source_systems_source_system_name ON source_systems(source_system_name);
CREATE INDEX idx_source_systems_lifecycle_state ON source_systems(lifecycle_state);
CREATE INDEX idx_source_systems_effective_from ON source_systems(effective_from);
CREATE INDEX idx_source_systems_effective_to ON source_systems(effective_to);
CREATE INDEX idx_source_systems_governance_status ON source_systems(governance_status);
CREATE INDEX idx_source_systems_created_by ON source_systems(created_by);
CREATE INDEX idx_source_systems_created_on ON source_systems(created_on);
CREATE INDEX idx_source_systems_modified_by ON source_systems(modified_by);
CREATE INDEX idx_source_systems_modified_on ON source_systems(modified_on);
CREATE INDEX idx_source_systems_version_number ON source_systems(version_number);
CREATE INDEX idx_source_systems_previous_version_id ON source_systems(previous_version_id);
CREATE INDEX idx_source_objects_source_object_name ON source_objects(source_object_name);
CREATE INDEX idx_source_objects_lifecycle_state ON source_objects(lifecycle_state);
CREATE INDEX idx_source_objects_effective_from ON source_objects(effective_from);
CREATE INDEX idx_source_objects_effective_to ON source_objects(effective_to);
CREATE INDEX idx_source_objects_governance_status ON source_objects(governance_status);
CREATE INDEX idx_source_objects_created_by ON source_objects(created_by);
CREATE INDEX idx_source_objects_created_on ON source_objects(created_on);
CREATE INDEX idx_source_objects_modified_by ON source_objects(modified_by);
CREATE INDEX idx_source_objects_modified_on ON source_objects(modified_on);
CREATE INDEX idx_source_objects_version_number ON source_objects(version_number);
CREATE INDEX idx_source_objects_previous_version_id ON source_objects(previous_version_id);
CREATE INDEX idx_source_objects_source_system_id ON source_objects(source_system_id);
CREATE INDEX idx_institutional_acts_institutional_act_name ON institutional_acts(institutional_act_name);
CREATE INDEX idx_institutional_acts_lifecycle_state ON institutional_acts(lifecycle_state);
CREATE INDEX idx_institutional_acts_effective_from ON institutional_acts(effective_from);
CREATE INDEX idx_institutional_acts_effective_to ON institutional_acts(effective_to);
CREATE INDEX idx_institutional_acts_governance_status ON institutional_acts(governance_status);
CREATE INDEX idx_institutional_acts_created_by ON institutional_acts(created_by);
CREATE INDEX idx_institutional_acts_created_on ON institutional_acts(created_on);
CREATE INDEX idx_institutional_acts_modified_by ON institutional_acts(modified_by);
CREATE INDEX idx_institutional_acts_modified_on ON institutional_acts(modified_on);
CREATE INDEX idx_institutional_acts_version_number ON institutional_acts(version_number);
CREATE INDEX idx_institutional_acts_previous_version_id ON institutional_acts(previous_version_id);
CREATE INDEX idx_institutional_acts_governance_id ON institutional_acts(governance_id);
CREATE INDEX idx_institutional_acts_accountable_owner_id ON institutional_acts(accountable_owner_id);
CREATE INDEX idx_institutional_acts_decision_id ON institutional_acts(decision_id);
CREATE INDEX idx_institutional_acts_superseded_act_id ON institutional_acts(superseded_act_id);
CREATE INDEX idx_contexts_context_name ON contexts(context_name);
CREATE INDEX idx_contexts_lifecycle_state ON contexts(lifecycle_state);
CREATE INDEX idx_contexts_effective_from ON contexts(effective_from);
CREATE INDEX idx_contexts_effective_to ON contexts(effective_to);
CREATE INDEX idx_contexts_governance_status ON contexts(governance_status);
CREATE INDEX idx_contexts_created_by ON contexts(created_by);
CREATE INDEX idx_contexts_created_on ON contexts(created_on);
CREATE INDEX idx_contexts_modified_by ON contexts(modified_by);
CREATE INDEX idx_contexts_modified_on ON contexts(modified_on);
CREATE INDEX idx_contexts_version_number ON contexts(version_number);
CREATE INDEX idx_contexts_previous_version_id ON contexts(previous_version_id);

-- ---------- HARD RULE: Universal Relationship Principle (GMR-032) ----------
-- No Enterprise-Entity-to-Enterprise-Entity relationship may be added as a direct
-- FK column anywhere in this schema. Every such relationship goes through
-- institutional_relationships (from_entity_id/to_entity_id) or through
-- assertions (subject_entity_id/object_entity_id) at the predication layer.
-- Audited as of v1.3: no violation exists in this file. Scoped to entity-to-entity
-- relationships specifically; whether it extends to structural FKs internal to the
-- constitutional pipeline (e.g. decisions.decision_state_id) is a separate, larger
-- question, deliberately left open here, not decided.

-- ---------- BOUNDED NON-CANONICAL EXTENSIONS (CDD-012, CDD-013) ----------

-- CDD-013 bounded non-canonical application-security record (Physical Model v1.5)
CREATE TABLE api_security_audit_events (
    audit_event_id UUID PRIMARY KEY,
    event_timestamp TIMESTAMPTZ NOT NULL,
    tenant_id VARCHAR(200),
    principal_reference VARCHAR(200),
    operation VARCHAR(100) NOT NULL,
    endpoint_classification VARCHAR(100) NOT NULL,
    event_category VARCHAR(80) NOT NULL,
    outcome VARCHAR(40) NOT NULL,
    diagnostic_code VARCHAR(100) NOT NULL,
    correlation_id UUID NOT NULL,
    execution_id UUID,
    attempt_id UUID,
    authorization_decision_reference VARCHAR(200),
    evidence_resource_reference VARCHAR(300),
    source_channel VARCHAR(100),
    retention_until TIMESTAMPTZ NOT NULL,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    legal_hold_reference VARCHAR(200),
    integrity_version INTEGER NOT NULL DEFAULT 1,
    integrity_digest BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT api_security_audit_retention_valid CHECK (retention_until >= event_timestamp)
);
CREATE INDEX ix_api_security_audit_tenant_time ON api_security_audit_events (tenant_id, event_timestamp);
CREATE INDEX ix_api_security_audit_category_time ON api_security_audit_events (event_category, event_timestamp);
CREATE INDEX ix_api_security_audit_correlation ON api_security_audit_events (correlation_id);
CREATE INDEX ix_api_security_audit_retention ON api_security_audit_events (retention_until, legal_hold);
-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.3
-- Generated directly from EAD-001 v1.3 (Enterprise Attribute Dictionary)

CREATE TABLE runtime_executions (
 execution_id UUID PRIMARY KEY, logical_execution_id UUID NOT NULL, tenant_id VARCHAR(200) NOT NULL,
 protocol_version VARCHAR(32) NOT NULL, integration_contract_version VARCHAR(32) NOT NULL,
 request_id UUID NOT NULL, correlation_id UUID NOT NULL, session_id UUID NOT NULL,
 request_classification VARCHAR(100) NOT NULL, payload_fingerprint BYTEA NOT NULL,
 control_fingerprint BYTEA NOT NULL, state VARCHAR(32) NOT NULL, admitted_at TIMESTAMPTZ NOT NULL,
 terminal_at TIMESTAMPTZ, revision BIGINT NOT NULL DEFAULT 0, legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
 retention_until TIMESTAMPTZ, UNIQUE (tenant_id, protocol_version, request_id)
);
CREATE INDEX idx_runtime_executions_recovery ON runtime_executions (tenant_id, state, admitted_at);
CREATE TABLE runtime_stages (
 stage_id UUID PRIMARY KEY, execution_id UUID NOT NULL REFERENCES runtime_executions(execution_id),
 stage_name VARCHAR(16) NOT NULL, stage_ordinal INTEGER NOT NULL, status VARCHAR(32) NOT NULL,
 started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ, input_handoff_id UUID,
 output_handoff_id UUID, safe_failure_code VARCHAR(100), revision BIGINT NOT NULL DEFAULT 0,
 UNIQUE (execution_id, stage_ordinal)
);
CREATE TABLE runtime_handoffs (
 handoff_id UUID PRIMARY KEY, execution_id UUID NOT NULL REFERENCES runtime_executions(execution_id),
 source_stage VARCHAR(16), target_stage VARCHAR(16), contract_version VARCHAR(32) NOT NULL,
 protected_payload BYTEA NOT NULL, content_hash BYTEA NOT NULL, created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE runtime_artifact_references (
 artifact_reference_id UUID PRIMARY KEY, execution_id UUID NOT NULL REFERENCES runtime_executions(execution_id),
 stage_id UUID REFERENCES runtime_stages(stage_id), artifact_role VARCHAR(40) NOT NULL,
 artifact_id UUID NOT NULL, source_capability VARCHAR(16) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 UNIQUE (execution_id, artifact_role, artifact_id)
);
CREATE TABLE runtime_results (
 result_id UUID PRIMARY KEY, execution_id UUID NOT NULL UNIQUE REFERENCES runtime_executions(execution_id),
 terminal_capability VARCHAR(16), disposition VARCHAR(40) NOT NULL, result_code VARCHAR(100),
 result_value VARCHAR(200), actionable BOOLEAN NOT NULL, completed_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE runtime_recovery_attempts (
 recovery_id UUID PRIMARY KEY, logical_execution_id UUID NOT NULL,
 original_execution_id UUID NOT NULL REFERENCES runtime_executions(execution_id),
 replay_execution_id UUID NOT NULL UNIQUE REFERENCES runtime_executions(execution_id),
 checkpoint_stage_id UUID REFERENCES runtime_stages(stage_id), tenant_id VARCHAR(200) NOT NULL,
 replay_principal_id VARCHAR(200) NOT NULL, original_authorization_reference VARCHAR(200) NOT NULL,
 replay_authorization_reference VARCHAR(200) NOT NULL, replay_reason VARCHAR(1000) NOT NULL,
 correlation_id UUID NOT NULL, authorized_at TIMESTAMPTZ NOT NULL
);
