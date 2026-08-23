"""Request/response models for the Gate M Ontology Modeling API (CDD-028;
Gate M Artifact Authorization v1.1 §10). Every response field comes from an
already-persisted `OntologyChangeProposal` column."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProposeRequest(BaseModel):
    """`proposal_kind` discriminates the request shape: `CreateConcept`
    requires `entity_type_name` (and optionally `definition`);
    `CreateRelationship` requires `relationship_type_name`,
    `source_entity_type_id`, and `target_entity_type_id`. The router
    enforces the correct combination; the domain layer's own `__post_init__`
    re-enforces it independently (AA v1.1 §4.1)."""

    proposal_kind: str
    entity_type_name: str | None = None
    definition: str | None = None
    relationship_type_name: str | None = None
    source_entity_type_id: UUID | None = None
    target_entity_type_id: UUID | None = None


class RejectRequest(BaseModel):
    rejection_reason: str | None = None


class ProposalResponse(BaseModel):
    ontology_change_proposal_id: UUID
    proposal_kind: str
    status: str
    proposed_entity_type_name: str | None
    proposed_definition: str | None
    proposed_relationship_type_name: str | None
    proposed_source_entity_type_id: UUID | None
    proposed_target_entity_type_id: UUID | None
    proposed_by: str
    proposed_on: datetime
    approved_by: str | None
    approved_on: datetime | None
    rejected_by: str | None
    rejected_on: datetime | None
    rejection_reason: str | None
    published_by: str | None
    published_on: datetime | None
    published_entity_type_id: UUID | None
    published_relationship_type_id: UUID | None


class ProposalListResponse(BaseModel):
    proposals: list[ProposalResponse]
