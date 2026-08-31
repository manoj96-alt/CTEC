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

export interface RemediationCandidateView {
  candidate_id: string;
  proposed_value: string;
  status: string;
}

export interface RemediationAuthorizationView {
  authorization_id: string;
  principal: string;
  decided_on: string | null;
  instruction: string;
  authorized_against_state_revision: number;
  is_stale: boolean;
  status: string;
}

export interface RemediationExternalExecutionView {
  reported_at: string;
}

export interface RemediationResponse {
  case_status: string | null;
  candidate: RemediationCandidateView | null;
  recommendation: AgentRecommendationView | null;
  authorization: RemediationAuthorizationView | null;
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
