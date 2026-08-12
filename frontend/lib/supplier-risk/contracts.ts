export type ExecutionState = "Accepted" | "Executing" | "Completed" | "Failed";
export type TerminalClassification =
  | "IN_PROGRESS"
  | "APPROVED"
  | "CONDITIONALLY_APPROVED"
  | "REJECTED"
  | "INDETERMINATE"
  | "BUSINESS_GATED"
  | "TECHNICAL_FAILURE";

export interface ExecutionSummary {
  logical_execution_identifier: string;
  current_execution_identifier: string;
  subject_summary: string;
  submitted_at: string;
  execution_status: ExecutionState;
  current_or_terminal_stage: string | null;
  terminal_classification: TerminalClassification | null;
  retry_eligible: boolean;
  replay_eligible: boolean;
  last_updated_at: string;
  revision: number;
}
export interface ExecutionList {
  items: ExecutionSummary[];
  next_cursor: string | null;
}
export interface SubmissionResponse {
  execution_identifier: string;
  logical_execution_identifier: string;
  correlation_identifier: string;
  state: ExecutionState;
}
export interface Attempt {
  execution_identifier: string;
  logical_execution_identifier: string;
  state: ExecutionState;
  admitted_at: string;
  completed_at: string | null;
  revision: number;
}
export interface Stage {
  stage_identifier: string;
  stage_name: "ERM" | "SRM" | "ASM" | "KRM" | "DRM" | "GRM";
  stage_ordinal: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  safe_failure_code: string | null;
  produced_record_references: string[];
}
export interface GovernedResult {
  execution_identifier: string;
  governance_standing: string | null;
  recommendation: string | null;
  actionable: boolean;
  completed_at: string;
  produced_record_references: string[];
  terminal_classification: TerminalClassification;
  safe_diagnostic_code: string | null;
  conditions: string[];
  verified_conditions: string[];
  safe_business_explanation: string | null;
  evidence_references: string[];
  provenance_references: string[];
  policy_reference: string | null;
  policy_version: string | null;
  policy_rule: string | null;
  decision_reference: string | null;
  contract_version: "PAS-001-v1.1";
  ontology_id: string | null;
  ontology_version: string | null;
  ontology_status: string | null;
  applicable_concept_ids: string[];
  applicable_relationship_ids: string[];
  ontology_quality_score: number | null;
  semantic_path: string | null;
}
export interface RetryEligibility {
  eligible: boolean;
  governing_attempt_identifier: string;
  reason_code: string;
  safe_constraint: string | null;
  revision: number;
  action: string | null;
}
export interface ReplayOption {
  option_reference: string;
  source_attempt_identifier: string;
  stage_label: string;
  checkpoint_at: string;
  eligible: boolean;
  reason_code: string;
  revision: number;
}
export interface ApiProblem {
  code: string;
  message: string;
  correlation_id: string;
  retryable: boolean;
}
export interface AssessmentDraft {
  supplierName: string;
  sourceObjectId: string;
  enterpriseEntityId: string;
  enterpriseCanonicalName: string;
  institutionalConceptId: string;
  semanticLabel: string;
  contextId: string;
  materialId: string;
  facilityOrRegionId: string;
  sourceSystemId: string;
  sourceRecordReference: string;
  observationId: string;
  observationValue: string;
  evidenceReference: string;
  severity: "LOW" | "MATERIAL" | "HIGH" | "CRITICAL";
  observedAt: string;
  effectiveAt: string;
  identityScore: number;
  semanticScore: number;
  assertionScore: number;
  knowledgeScore: number;
  decisionScore: number;
  governanceScore: number;
  identityPolicyVersion: string;
  semanticPolicyVersion: string;
  assertionPolicyVersion: string;
  knowledgePolicyVersion: string;
  decisionPolicyReference: string;
  decisionPolicyVersion: string;
  decisionPolicyRule: string;
  governancePolicyReference: string;
  governancePolicyVersion: string;
}
