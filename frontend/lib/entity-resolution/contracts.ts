// Mirrors backend/app/api/entity_resolution/schemas.py exactly. Every
// field here is either persisted data or a value already computed by the
// backend (Gate B's evidence engine / Gate C's decision service) -- the
// frontend never re-derives evidence, scores, or outcomes on its own.

export type ResolutionOutcome =
  | "Resolved"
  | "Possible Resolution"
  | "Unresolved"
  | "Blocked Conflict";

export type BusinessConfidence = "High" | "Medium" | "Low";

export type EvidenceClassification = "Positive" | "Negative" | "Missing" | "Veto";

export type StewardDecisionAction =
  | "confirm_match"
  | "reject_match"
  | "mark_unresolved"
  | "block_conflict";

export interface EvidenceItem {
  evidence_type: string;
  compared_attributes: string[];
  normalized_values: string[];
  classification: EvidenceClassification;
  contribution: number;
  explanation: string;
  provenance: string;
}

export interface EvidenceProfile {
  items: EvidenceItem[];
}

export interface SourceRepresentationSummary {
  source_object_id: string;
  source_object_name: string;
  source_system_id: string;
  source_system_name: string;
}

export interface PriorDecisionSummary {
  record_id: string;
  outcome: ResolutionOutcome;
  business_confidence: BusinessConfidence;
  produced_at: string;
  actor_id: string | null;
  decision_rationale: string | null;
}

export interface CaseSummary {
  understanding_key: string;
  record_id: string;
  outcome: ResolutionOutcome;
  business_confidence: BusinessConfidence;
  policy_version: string;
  produced_at: string;
  supporting_source_object_count: number;
  candidate_enterprise_entity_id: string | null;
  candidate_enterprise_entity_name: string | null;
}

export interface CaseList {
  items: CaseSummary[];
}

export interface CaseDetail {
  understanding_key: string;
  record_id: string;
  outcome: ResolutionOutcome;
  business_confidence: BusinessConfidence;
  structured_reasons: string[];
  narrative_explanation: string;
  produced_at: string;
  policy_id: string | null;
  policy_name: string | null;
  policy_version: string;
  evidence_profile: EvidenceProfile | null;
  candidate_enterprise_entity_id: string | null;
  candidate_enterprise_entity_name: string | null;
  source_representations: SourceRepresentationSummary[];
  actor_id: string | null;
  decision_rationale: string | null;
  prior_decision_count: number;
  previous_decision: PriorDecisionSummary | null;
}

export interface PolicySummary {
  policy_id: string;
  policy_name: string;
  policy_version: string;
  preset_kind: string;
  resolved_threshold: number;
  possible_threshold: number;
  high_confidence_threshold: number;
  medium_confidence_threshold: number;
  min_corroborating_attributes: number;
  country_conflict_severity: "veto" | "review";
  parent_subsidiary_conflict_severity: "veto" | "review";
}

export interface PolicyList {
  items: PolicySummary[];
}

export interface PreviewResult {
  policy_id: string;
  policy_name: string;
  policy_version: string;
  outcome: ResolutionOutcome;
  business_confidence: BusinessConfidence;
  score: number;
  would_change_outcome: boolean;
  structured_reasons: string[];
}

export interface DecisionRequestBody {
  action: StewardDecisionAction;
  rationale: string;
  based_on_record_id: string;
  policy_id: string;
}

export interface DecisionResult {
  record_id: string;
  understanding_key: string;
  outcome: ResolutionOutcome;
  business_confidence: BusinessConfidence;
  produced_at: string;
  policy_id: string | null;
  policy_version: string;
  narrative_explanation: string;
  structured_reasons: string[];
}

export interface ApiProblem {
  code: string;
  message: string;
  correlation_id: string;
  retryable: boolean;
}
