// Mirrors the existing, unmodified CDD-034 `ResolveRequest`/`ResolveResponse`
// schema exactly (backend/app/api/information_element_evidence_fitness/
// schemas.py; CDD-034 §8-§9). No field is added, renamed, or inferred.

export interface ResolveRequest {
  blueprint_name: string;
  information_element_name: string;
}

export type FitnessStatus = "FIT" | "STALE" | "CONFLICTING";

export interface ResolveResponse {
  information_element_requirement_id: string;
  source_field_id: string | null;
  fitness_status: FitnessStatus | null;
  evaluated_at: string;
}
