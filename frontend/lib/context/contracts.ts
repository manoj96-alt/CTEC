// Mirrors the existing, unmodified Gate O `ResolveRequest`/`ResolveResponse`
// schema exactly (backend/app/api/information_element_context/schemas.py;
// CDD-029 §11-§12). No field is added, renamed, or inferred.

export interface ResolveRequest {
  blueprint_name: string;
  information_element_name: string;
}

export interface ResolveResponse {
  blueprint_id: string;
  blueprint_version_number: number;
  information_element_requirement_id: string;
  information_element_name: string;
  obligation: string;
  coverage_status: string;
  evidence_availability_status: string | null;
}
