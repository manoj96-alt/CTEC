// TypeScript mirror of backend/app/api/oqi/schemas.py (CDD-045 §23). Every
// enum field is the exact governed string value coming back from the API --
// this file never redefines, widens, or reinterprets a domain state. No
// trust/health/confidence score field exists here because none exists on
// the backend contract (CDD-045 §8).

export interface CommandCenterResponse {
  reliance_supported_count: number;
  reliance_at_risk_count: number;
  reliance_unknown_count: number;
  critical_dependencies_at_risk_count: number;
  open_findings_count: number;
  active_agent_investigations_count: number;
  pending_human_authorizations_count: number;
}

export interface FindingSummary {
  finding_id: string;
  finding_family: string;
  condition_label: string;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
  affected_entity_id: string | null;
  affected_entity_type: string | null;
  highest_criticality: string | null;
  reliance_state: string | null;
}

export interface FindingListResponse {
  items: FindingSummary[];
  next_cursor: string | null;
}

export interface FindingDetailResponse {
  finding_id: string;
  finding_family: string;
  condition_label: string;
  status: string;
  state_revision: number;
  first_seen_at: string;
  last_seen_at: string;
}

export interface EvidenceParticipant {
  source_system: string;
  observed_value: string | null;
  is_missing: boolean;
  is_authoritative: boolean;
  is_conflicting: boolean;
}

export interface EvidenceCandidate {
  candidate_id: string;
  proposed_value: string;
  supporting_participant_count: number;
  status: string;
}

export interface EvidenceResponse {
  participants: EvidenceParticipant[];
  candidate: EvidenceCandidate | null;
}

export interface OntologyImpactPathSegment {
  relationship_instance_id: string;
  path_ordinal: number;
  direction: string;
}

export interface OntologyImpactResponse {
  outcome: string;
  direct_entity_id: string | null;
  direct_entity_type: string | null;
  propagated_path: OntologyImpactPathSegment[] | null;
}

export interface BusinessImpactDependency {
  business_process_name: string;
  criticality: string | null;
  business_dependency_version: number;
}

export interface BusinessImpactResponse {
  outcome: string;
  dependencies: BusinessImpactDependency[];
}

export interface RelianceHistoryEntry {
  state: string;
  evaluated_at: string;
}

export interface RelianceResponse {
  state: string;
  reason_codes: string[];
  contributing_finding_ids: string[];
  history: RelianceHistoryEntry[];
}

export interface SpecialistAssessmentView {
  role_id: string;
  result_state: string;
  assessment_text: string | null;
  referenced_candidate_id: string | null;
}

export interface AgentRecommendationView {
  recommendation_type: string;
  candidate_id: string | null;
  rationale: string;
  basis: string;
}

export interface AgentInvestigationResponse {
  specialists: SpecialistAssessmentView[];
  recommendation: AgentRecommendationView | null;
}

// CDD-085 G-R3 §7/§13: one candidate's own authorization -- never a
// case-wide "the" authorization picked arbitrarily from among siblings.
export interface RemediationCandidateAuthorizationView {
  authorization_id: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED";
  requested_by: string;
  requested_on: string;
  decided_by: string | null;
  decided_on: string | null;
  rejection_reason: string | null;
  is_stale: boolean;
}

export interface RemediationCandidateItemView {
  candidate_id: string;
  proposed_value: string;
  basis: string;
  authorization: RemediationCandidateAuthorizationView | null;
}

export interface RemediationExternalExecutionView {
  reported_at: string;
}

// CDD-085 G-R3 §7-§9/§16/§17: the plural remediation read model -- every
// candidate the last Prepare produced, deterministically ordered, each
// carrying its own authorization. Replaces the prior singular
// candidate/authorization fields, which collapsed a genuine
// CROSS_SOURCE_VALUE_CONFLICT case (e.g. Golden's real US/MX candidates)
// to one arbitrary candidate.
export interface RemediationResponse {
  case_status: string | null;
  candidates: RemediationCandidateItemView[];
  recommendation: AgentRecommendationView | null;
  external_execution: RemediationExternalExecutionView | null;
}

export interface DecideAuthorizationRequest {
  approve: boolean;
  decided_by: string;
  rejection_reason?: string | null;
}

export interface RemediationCaseActionResponse {
  case_status: string;
}
