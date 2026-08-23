// Mirrors backend/app/api/ontology_modeling/schemas.py exactly. Every field
// here is either request input the user typed or already-persisted
// OntologyChangeProposal data -- this file never computes a canonical
// ontology value on its own, and nothing here ever represents a canonical
// entity_types/relationship_types row directly (only the ids Gate M's own
// PUBLISH step later attributed to a proposal, once it exists).

export type ProposalKind = "CreateConcept" | "CreateRelationship";

export type ProposalStatus = "Proposed" | "Approved" | "Rejected" | "Published";

export interface ProposeConceptBody {
  proposal_kind: "CreateConcept";
  entity_type_name: string;
  definition?: string | null;
}

export interface ProposeRelationshipBody {
  proposal_kind: "CreateRelationship";
  relationship_type_name: string;
  source_entity_type_id: string;
  target_entity_type_id: string;
}

export interface RejectBody {
  rejection_reason?: string | null;
}

export interface ProposalDetail {
  ontology_change_proposal_id: string;
  proposal_kind: ProposalKind;
  status: ProposalStatus;
  proposed_entity_type_name: string | null;
  proposed_definition: string | null;
  proposed_relationship_type_name: string | null;
  proposed_source_entity_type_id: string | null;
  proposed_target_entity_type_id: string | null;
  proposed_by: string;
  proposed_on: string;
  approved_by: string | null;
  approved_on: string | null;
  rejected_by: string | null;
  rejected_on: string | null;
  rejection_reason: string | null;
  published_by: string | null;
  published_on: string | null;
  published_entity_type_id: string | null;
  published_relationship_type_id: string | null;
}

export interface ProposalList {
  proposals: ProposalDetail[];
}

// backend/app/api/ontology_modeling/router.py does not register its path
// under main.py's _STABLE_ERROR_CONTRACT_PATHS allowlist (out of scope for
// this Artifact Authorization -- that tuple literal is not the one
// authorized router-registration line) -- errors arrive as the generic
// FastAPI {"detail": {"code": ...}} shape, not the flattened ApiProblem
// shape entity-resolution/ontology-copilot use.
export interface OntologyModelingProblem {
  code: string;
}
