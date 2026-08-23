"""Domain model for `OntologyChangeProposal` (Gate M; CDD-028 §12-§13,
§17; Gate M Artifact Authorization v1.1 §4.1). A non-canonical, net-new-only
proposal artifact: it confers no ontology authority of its own, is never
read by `app.domain.ontology.resolver`, and exists solely to carry a
candidate Concept or Relationship from MODEL through PUBLISH. Distinct from
`GovernanceStatus` -- `ProposalStatus` describes this artifact's own
workflow state, not a canonical row's state. Provenance fields
(`proposed_by`/`approved_by`/`rejected_by`/`published_by`) are plain,
unconstrained strings -- never `Identifier`, never `enterprise_entities`-FK
-- following `EnterpriseEntityResolutionRecord.actor_id`/
`ApiSecurityAuditEvent.principal_reference` precedent (AA v1.1 §15, §17)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier

_MAX_NAME_LENGTH = 200
_MAX_DEFINITION_LENGTH = 2000
_MAX_REJECTION_REASON_LENGTH = 1000


class ProposalKind(StrEnum):
    CREATE_CONCEPT = "CreateConcept"
    CREATE_RELATIONSHIP = "CreateRelationship"


class ProposalStatus(StrEnum):
    PROPOSED = "Proposed"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PUBLISHED = "Published"


@dataclass(frozen=True, slots=True)
class OntologyChangeProposal:
    ontology_change_proposal_id: Identifier
    proposal_kind: ProposalKind
    status: ProposalStatus
    proposed_entity_type_name: str | None
    proposed_definition: str | None
    proposed_relationship_type_name: str | None
    proposed_source_entity_type_id: Identifier | None
    proposed_target_entity_type_id: Identifier | None
    proposed_by: str
    proposed_on: datetime
    approved_by: str | None = None
    approved_on: datetime | None = None
    rejected_by: str | None = None
    rejected_on: datetime | None = None
    rejection_reason: str | None = None
    published_by: str | None = None
    published_on: datetime | None = None
    published_entity_type_id: Identifier | None = None
    published_relationship_type_id: Identifier | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.proposal_kind, ProposalKind):
            raise ValidationException("Proposal Kind must be a Proposal Kind")
        if not isinstance(self.status, ProposalStatus):
            raise ValidationException("Status must be a Proposal Status")

        for field_name, identifier_value in (
            ("Ontology Change Proposal ID", self.ontology_change_proposal_id),
            ("Proposed Source Entity Type", self.proposed_source_entity_type_id),
            ("Proposed Target Entity Type", self.proposed_target_entity_type_id),
            ("Published Entity Type", self.published_entity_type_id),
            ("Published Relationship Type", self.published_relationship_type_id),
        ):
            if identifier_value is not None and not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")

        for field_name, actor_value in (
            ("Proposed By", self.proposed_by),
            ("Approved By", self.approved_by),
            ("Rejected By", self.rejected_by),
            ("Published By", self.published_by),
        ):
            if actor_value is not None and not isinstance(actor_value, str):
                raise ValidationException(f"{field_name} must be a plain string")
            if isinstance(actor_value, str) and not actor_value.strip():
                raise ValidationException(f"{field_name} must not be blank")

        if self.proposed_by is None:
            raise ValidationException("Proposed By is required")

        if self.rejection_reason is not None:
            if not isinstance(self.rejection_reason, str):
                raise ValidationException("Rejection Reason must be a string")
            if len(self.rejection_reason) > _MAX_REJECTION_REASON_LENGTH:
                raise ValidationException(
                    f"Rejection Reason must not exceed {_MAX_REJECTION_REASON_LENGTH} characters"
                )

        for field_name, timestamp in (
            ("Proposed On", self.proposed_on),
            ("Approved On", self.approved_on),
            ("Rejected On", self.rejected_on),
            ("Published On", self.published_on),
        ):
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValidationException(f"{field_name} must include a timezone")
        if self.proposed_on is None:
            raise ValidationException("Proposed On is required")

        if self.proposal_kind is ProposalKind.CREATE_CONCEPT:
            self._validate_concept_shape()
        else:
            self._validate_relationship_shape()

    def _validate_concept_shape(self) -> None:
        if not self.proposed_entity_type_name or not self.proposed_entity_type_name.strip():
            raise ValidationException(
                "Proposed Entity Type Name is required for a CreateConcept proposal"
            )
        if len(self.proposed_entity_type_name) > _MAX_NAME_LENGTH:
            raise ValidationException(
                f"Proposed Entity Type Name must not exceed {_MAX_NAME_LENGTH} characters"
            )
        if self.proposed_definition is not None and len(self.proposed_definition) > (
            _MAX_DEFINITION_LENGTH
        ):
            raise ValidationException(
                f"Proposed Definition must not exceed {_MAX_DEFINITION_LENGTH} characters"
            )
        if self.proposed_relationship_type_name is not None:
            raise ValidationException(
                "Proposed Relationship Type Name must be None for a CreateConcept proposal"
            )
        if self.proposed_source_entity_type_id is not None:
            raise ValidationException(
                "Proposed Source Entity Type must be None for a CreateConcept proposal"
            )
        if self.proposed_target_entity_type_id is not None:
            raise ValidationException(
                "Proposed Target Entity Type must be None for a CreateConcept proposal"
            )

    def _validate_relationship_shape(self) -> None:
        if (
            not self.proposed_relationship_type_name
            or not self.proposed_relationship_type_name.strip()
        ):
            raise ValidationException(
                "Proposed Relationship Type Name is required for a CreateRelationship proposal"
            )
        if len(self.proposed_relationship_type_name) > _MAX_NAME_LENGTH:
            raise ValidationException(
                f"Proposed Relationship Type Name must not exceed {_MAX_NAME_LENGTH} characters"
            )
        if self.proposed_source_entity_type_id is None:
            raise ValidationException(
                "Proposed Source Entity Type is required for a CreateRelationship proposal"
            )
        if self.proposed_target_entity_type_id is None:
            raise ValidationException(
                "Proposed Target Entity Type is required for a CreateRelationship proposal"
            )
        if self.proposed_entity_type_name is not None:
            raise ValidationException(
                "Proposed Entity Type Name must be None for a CreateRelationship proposal"
            )
        if self.proposed_definition is not None:
            raise ValidationException(
                "Proposed Definition must be None for a CreateRelationship proposal"
            )
