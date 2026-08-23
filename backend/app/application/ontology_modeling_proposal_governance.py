"""Gate M -- Governed Visual Ontology Modeling proposal governance and
publication (CDD-028 §12-§20; Gate M Artifact Authorization v1.1 §4.4,
§12-§15, §18-§20). Net-new-only: `propose_concept`/`propose_relationship`
validate and persist a candidate exclusively via the non-canonical
`OntologyChangeProposalRepository`; `approve`/`reject` transition the same
proposal row's own status (AA v1.1 §12 -- a deliberate departure from Gate
L's row-immutability convention, since here the proposal itself, not a
canonical entity, is tracked); `publish` is the sole method in this entire
module that ever writes to `entity_types`, `institutional_concepts`,
`relationship_types`, or `ontology_relationship_bindings` -- and it does so
using only `session.add()` with `governance_status="Approved"`,
`version_number=1`, `previous_version_id=None`,
`created_by=BOOTSTRAP_SYSTEM_ENTITY_ID`, identical in shape to every row
`OntologySeeder` has ever written (AA v1.1 §9, §13). `principal.principal_id`
is never written to any `enterprise_entities`-FK or `entity_types`/
`relationship_types`-FK column, anywhere in this module -- it is recorded
only on `OntologyChangeProposal`'s own plain-string provenance fields (AA
v1.1 §15, §17). Never calls `entity_type_repository.py`/
`relationship_type_repository.py` (both remain unused)."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.core.bootstrap import BOOTSTRAP_ENTERPRISE_ID, BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.ontology_modeling.proposal import (
    OntologyChangeProposal,
    ProposalKind,
    ProposalStatus,
)
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.models.entity_type import EntityType as EntityTypeORM
from app.infrastructure.persistence.models.institutional_concept import (
    InstitutionalConcept as InstitutionalConceptORM,
)
from app.infrastructure.persistence.models.ontology_relationship_binding import (
    OntologyRelationshipBinding as OntologyRelationshipBindingORM,
)
from app.infrastructure.persistence.models.relationship_type import (
    RelationshipType as RelationshipTypeORM,
)
from app.infrastructure.persistence.ontology_change_proposal_repository import (
    OntologyChangeProposalRepository,
)


class OntologyModelingProposalGovernanceApplicationService:
    def __init__(
        self,
        *,
        session: Session,
        proposal_repository: OntologyChangeProposalRepository,
    ) -> None:
        self._session = session
        self._proposal_repository = proposal_repository

    def propose_concept(
        self,
        *,
        principal: TrustedPrincipal,
        entity_type_name: str,
        definition: str | None,
        now: datetime | None = None,
    ) -> OntologyChangeProposal:
        self._require_principal(principal)
        proposal = OntologyChangeProposal(
            ontology_change_proposal_id=Identifier(uuid4()),
            proposal_kind=ProposalKind.CREATE_CONCEPT,
            status=ProposalStatus.PROPOSED,
            proposed_entity_type_name=entity_type_name,
            proposed_definition=definition,
            proposed_relationship_type_name=None,
            proposed_source_entity_type_id=None,
            proposed_target_entity_type_id=None,
            proposed_by=principal.principal_id,
            proposed_on=now if now is not None else datetime.now(UTC),
        )
        self._proposal_repository.create(proposal)
        return proposal

    def propose_relationship(
        self,
        *,
        principal: TrustedPrincipal,
        relationship_type_name: str,
        source_entity_type_id: Identifier,
        target_entity_type_id: Identifier,
        now: datetime | None = None,
    ) -> OntologyChangeProposal:
        self._require_principal(principal)
        self._validate_endpoint("source", source_entity_type_id)
        self._validate_endpoint("target", target_entity_type_id)
        proposal = OntologyChangeProposal(
            ontology_change_proposal_id=Identifier(uuid4()),
            proposal_kind=ProposalKind.CREATE_RELATIONSHIP,
            status=ProposalStatus.PROPOSED,
            proposed_entity_type_name=None,
            proposed_definition=None,
            proposed_relationship_type_name=relationship_type_name,
            proposed_source_entity_type_id=source_entity_type_id,
            proposed_target_entity_type_id=target_entity_type_id,
            proposed_by=principal.principal_id,
            proposed_on=now if now is not None else datetime.now(UTC),
        )
        self._proposal_repository.create(proposal)
        return proposal

    def _validate_endpoint(self, label: str, entity_type_id: Identifier) -> None:
        """Non-binding, UX-quality pre-check (AA v1.1 §4.4) -- proves the
        referenced EntityType exists/Active/Approved *before* the proposal
        is even created, so a nonexistent endpoint is rejected as a clean
        `ValidationException` rather than surfacing later as a deferred FK
        violation at commit time. `publish()`'s own live re-validation
        (§_publish_relationship) remains the sole binding check."""
        endpoint = self._session.execute(
            select(EntityTypeORM.lifecycle_state, EntityTypeORM.governance_status).where(
                EntityTypeORM.entity_type_id == entity_type_id.value
            )
        ).one_or_none()
        if endpoint is None:
            raise ValidationException(
                f"Relationship {label} EntityType does not exist: {entity_type_id.value}"
            )
        lifecycle_state, governance_status = endpoint
        if lifecycle_state != "Active" or governance_status != "Approved":
            raise ValidationException(
                f"Relationship {label} EntityType is not an Active, Approved concept: "
                f"{entity_type_id.value}"
            )

    def approve(
        self,
        *,
        principal: TrustedPrincipal,
        proposal: OntologyChangeProposal,
        now: datetime | None = None,
    ) -> OntologyChangeProposal:
        self._require_principal(principal)
        if proposal.status is not ProposalStatus.PROPOSED:
            raise ValidationException("Only a Proposed OntologyChangeProposal may be approved")
        approved = replace(
            proposal,
            status=ProposalStatus.APPROVED,
            approved_by=principal.principal_id,
            approved_on=now if now is not None else datetime.now(UTC),
        )
        self._proposal_repository.update_status(approved)
        return approved

    def reject(
        self,
        *,
        principal: TrustedPrincipal,
        proposal: OntologyChangeProposal,
        rejection_reason: str | None,
        now: datetime | None = None,
    ) -> OntologyChangeProposal:
        self._require_principal(principal)
        if proposal.status is not ProposalStatus.PROPOSED:
            raise ValidationException("Only a Proposed OntologyChangeProposal may be rejected")
        rejected = replace(
            proposal,
            status=ProposalStatus.REJECTED,
            rejected_by=principal.principal_id,
            rejected_on=now if now is not None else datetime.now(UTC),
            rejection_reason=rejection_reason,
        )
        self._proposal_repository.update_status(rejected)
        return rejected

    def publish(
        self,
        *,
        principal: TrustedPrincipal,
        proposal: OntologyChangeProposal,
        now: datetime | None = None,
    ) -> OntologyChangeProposal:
        self._require_principal(principal)
        if proposal.status is not ProposalStatus.APPROVED:
            raise ValidationException("Only an Approved OntologyChangeProposal may be published")

        publish_time = now if now is not None else datetime.now(UTC)
        published_entity_type_id: UUID | None = None
        published_relationship_type_id: UUID | None = None
        if proposal.proposal_kind is ProposalKind.CREATE_CONCEPT:
            published_entity_type_id = self._publish_concept(proposal, publish_time)
        else:
            published_relationship_type_id = self._publish_relationship(proposal, publish_time)

        published = replace(
            proposal,
            status=ProposalStatus.PUBLISHED,
            published_by=principal.principal_id,
            published_on=publish_time,
            published_entity_type_id=(
                Identifier(published_entity_type_id)
                if published_entity_type_id is not None
                else None
            ),
            published_relationship_type_id=(
                Identifier(published_relationship_type_id)
                if published_relationship_type_id is not None
                else None
            ),
        )
        self._proposal_repository.update_status(published)
        return published

    def _publish_concept(self, proposal: OntologyChangeProposal, now: datetime) -> UUID:
        assert proposal.proposed_entity_type_name is not None
        existing_concept = self._session.scalar(
            select(InstitutionalConceptORM.institutional_concept_id).where(
                InstitutionalConceptORM.institutional_concept_name
                == proposal.proposed_entity_type_name
            )
        )
        existing_entity_type = self._session.scalar(
            select(EntityTypeORM.entity_type_id).where(
                EntityTypeORM.entity_type_name == proposal.proposed_entity_type_name
            )
        )
        if existing_concept is not None or existing_entity_type is not None:
            raise ValidationException(
                f"Concept name already exists in the canonical ontology: "
                f"{proposal.proposed_entity_type_name!r}"
            )

        concept_id = uuid4()
        entity_type_id = uuid4()
        self._session.add(
            InstitutionalConceptORM(
                institutional_concept_id=concept_id,
                institutional_concept_name=proposal.proposed_entity_type_name,
                lifecycle_state="Active",
                effective_from=now,
                effective_to=None,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=now,
                modified_by=None,
                modified_on=None,
                version_number=1,
                previous_version_id=None,
                enterprise_id=BOOTSTRAP_ENTERPRISE_ID,
            )
        )
        self._session.flush()
        self._session.add(
            EntityTypeORM(
                entity_type_id=entity_type_id,
                entity_type_name=proposal.proposed_entity_type_name,
                lifecycle_state="Active",
                effective_from=now,
                effective_to=None,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=now,
                modified_by=None,
                modified_on=None,
                version_number=1,
                previous_version_id=None,
                institutional_concept_id=concept_id,
            )
        )
        self._session.flush()
        return entity_type_id

    def _publish_relationship(self, proposal: OntologyChangeProposal, now: datetime) -> UUID:
        assert proposal.proposed_relationship_type_name is not None
        assert proposal.proposed_source_entity_type_id is not None
        assert proposal.proposed_target_entity_type_id is not None

        existing_relationship_type = self._session.scalar(
            select(RelationshipTypeORM.relationship_type_id).where(
                RelationshipTypeORM.relationship_type_name
                == proposal.proposed_relationship_type_name
            )
        )
        if existing_relationship_type is not None:
            raise ValidationException(
                f"Relationship name already exists in the canonical ontology: "
                f"{proposal.proposed_relationship_type_name!r}"
            )

        self._validate_endpoint("source", proposal.proposed_source_entity_type_id)
        self._validate_endpoint("target", proposal.proposed_target_entity_type_id)

        relationship_type_id = uuid4()
        self._session.add(
            RelationshipTypeORM(
                relationship_type_id=relationship_type_id,
                relationship_type_name=proposal.proposed_relationship_type_name,
                lifecycle_state="Active",
                effective_from=now,
                effective_to=None,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=now,
                modified_by=None,
                modified_on=None,
                version_number=1,
                previous_version_id=None,
            )
        )
        self._session.flush()
        self._session.add(
            OntologyRelationshipBindingORM(
                binding_id=uuid4(),
                relationship_type_id=relationship_type_id,
                source_entity_type_id=proposal.proposed_source_entity_type_id.value,
                target_entity_type_id=proposal.proposed_target_entity_type_id.value,
                created_on=now,
            )
        )
        self._session.flush()
        return relationship_type_id

    def _require_principal(self, principal: TrustedPrincipal) -> None:
        if not isinstance(principal, TrustedPrincipal):
            raise ValidationException("A TrustedPrincipal is required for this action")
