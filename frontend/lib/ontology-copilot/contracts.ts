// Mirrors backend/app/api/ontology_copilot/schemas.py exactly. No field here
// is ever generated client-side; every value comes from the authenticated
// Gate D API response.

export type AskStatus =
  "answered" | "no_match" | "ambiguous_match" | "unsupported_question";

export interface ResolvedEntity {
  entity_id: string;
  entity_name: string;
  entity_type_name: string;
}

export interface EvidenceStep {
  step: number;
  entity_id: string;
  entity_name: string;
  entity_type_name: string;
  relationship_name: string | null;
}

export interface AskResponse {
  status: AskStatus;
  intent: string | null;
  answer: string;
  resolved_entity: ResolvedEntity | null;
  result_names: string[];
  evidence: EvidenceStep[][];
  reason: string | null;
}

export interface AskRequestBody {
  question: string;
}

export interface ApiProblem {
  code: string;
  message: string;
  correlation_id: string;
  retryable: boolean;
}
