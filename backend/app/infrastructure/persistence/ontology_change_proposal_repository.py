"""Repository for `OntologyChangeProposal` (Gate M; CDD-028 §12-§13; Gate M
Artifact Authorization v1.1 §4.3). Exposes exactly four members:
`create(...)`, `get_by_id(...)`, `update_status(...)`, `list(...)`.
`update_status(...)` performs a `SELECT ... FOR UPDATE` on the target row
before writing -- the row-level lock underpinning AA v1.1 §14's concurrency
guarantee -- and asserts the transition is one of the five valid ones (AA
v1.1 §12), raising `ValidationException` otherwise. No canonical
ontology table is read or written anywhere in this module."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.ontology_modeling.proposal import (
    OntologyChangeProposal,
    ProposalKind,
    ProposalStatus,
)
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.models.ontology_change_proposal import (
    OntologyChangeProposalORM,
)

_VALID_TRANSITIONS: dict[ProposalStatus, frozenset[ProposalStatus]] = {
    ProposalStatus.PROPOSED: frozenset({ProposalStatus.APPROVED, ProposalStatus.REJECTED}),
    ProposalStatus.APPROVED: frozenset({ProposalStatus.PUBLISHED}),
    ProposalStatus.REJECTED: frozenset(),
    ProposalStatus.PUBLISHED: frozenset(),
}


class OntologyChangeProposalRepository(Protocol):
    def create(self, proposal: OntologyChangeProposal) -> None: ...

    def get_by_id(self, ontology_change_proposal_id: UUID) -> OntologyChangeProposal | None: ...

    def update_status(self, proposal: OntologyChangeProposal) -> None: ...

    def list(self, *, status: ProposalStatus | None = None) -> list[OntologyChangeProposal]: ...


class OntologyChangeProposalRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, proposal: OntologyChangeProposal) -> None:
        self.session.add(_to_orm(proposal))

    def get_by_id(self, ontology_change_proposal_id: UUID) -> OntologyChangeProposal | None:
        model = self.session.get(OntologyChangeProposalORM, ontology_change_proposal_id)
        if model is None:
            return None
        return _to_domain(model)

    def update_status(self, proposal: OntologyChangeProposal) -> None:
        model = self.session.execute(
            select(OntologyChangeProposalORM)
            .where(
                OntologyChangeProposalORM.ontology_change_proposal_id
                == proposal.ontology_change_proposal_id.value
            )
            .with_for_update()
        ).scalar_one_or_none()
        if model is None:
            raise ValidationException(
                f"OntologyChangeProposal does not exist: {proposal.ontology_change_proposal_id.value}"
            )
        current_status = ProposalStatus(model.status)
        new_status = proposal.status
        if new_status not in _VALID_TRANSITIONS[current_status]:
            raise ValidationException(
                f"Invalid proposal transition: {current_status.value} -> {new_status.value}"
            )
        model.status = new_status.value
        model.approved_by = proposal.approved_by
        model.approved_on = proposal.approved_on
        model.rejected_by = proposal.rejected_by
        model.rejected_on = proposal.rejected_on
        model.rejection_reason = proposal.rejection_reason
        model.published_by = proposal.published_by
        model.published_on = proposal.published_on
        model.published_entity_type_id = (
            proposal.published_entity_type_id.value
            if proposal.published_entity_type_id is not None
            else None
        )
        model.published_relationship_type_id = (
            proposal.published_relationship_type_id.value
            if proposal.published_relationship_type_id is not None
            else None
        )

    def list(self, *, status: ProposalStatus | None = None) -> list[OntologyChangeProposal]:
        statement = select(OntologyChangeProposalORM).order_by(
            OntologyChangeProposalORM.proposed_on.desc()
        )
        if status is not None:
            statement = statement.where(OntologyChangeProposalORM.status == status.value)
        models = self.session.execute(statement).scalars().all()
        return [_to_domain(model) for model in models]


def _to_orm(proposal: OntologyChangeProposal) -> OntologyChangeProposalORM:
    return OntologyChangeProposalORM(
        ontology_change_proposal_id=proposal.ontology_change_proposal_id.value,
        proposal_kind=proposal.proposal_kind.value,
        status=proposal.status.value,
        proposed_entity_type_name=proposal.proposed_entity_type_name,
        proposed_definition=proposal.proposed_definition,
        proposed_relationship_type_name=proposal.proposed_relationship_type_name,
        proposed_source_entity_type_id=(
            proposal.proposed_source_entity_type_id.value
            if proposal.proposed_source_entity_type_id is not None
            else None
        ),
        proposed_target_entity_type_id=(
            proposal.proposed_target_entity_type_id.value
            if proposal.proposed_target_entity_type_id is not None
            else None
        ),
        proposed_by=proposal.proposed_by,
        proposed_on=proposal.proposed_on,
        approved_by=proposal.approved_by,
        approved_on=proposal.approved_on,
        rejected_by=proposal.rejected_by,
        rejected_on=proposal.rejected_on,
        rejection_reason=proposal.rejection_reason,
        published_by=proposal.published_by,
        published_on=proposal.published_on,
        published_entity_type_id=(
            proposal.published_entity_type_id.value
            if proposal.published_entity_type_id is not None
            else None
        ),
        published_relationship_type_id=(
            proposal.published_relationship_type_id.value
            if proposal.published_relationship_type_id is not None
            else None
        ),
    )


def _to_domain(model: OntologyChangeProposalORM) -> OntologyChangeProposal:
    return OntologyChangeProposal(
        ontology_change_proposal_id=Identifier(model.ontology_change_proposal_id),
        proposal_kind=ProposalKind(model.proposal_kind),
        status=ProposalStatus(model.status),
        proposed_entity_type_name=model.proposed_entity_type_name,
        proposed_definition=model.proposed_definition,
        proposed_relationship_type_name=model.proposed_relationship_type_name,
        proposed_source_entity_type_id=(
            Identifier(model.proposed_source_entity_type_id)
            if model.proposed_source_entity_type_id is not None
            else None
        ),
        proposed_target_entity_type_id=(
            Identifier(model.proposed_target_entity_type_id)
            if model.proposed_target_entity_type_id is not None
            else None
        ),
        proposed_by=model.proposed_by,
        proposed_on=model.proposed_on,
        approved_by=model.approved_by,
        approved_on=model.approved_on,
        rejected_by=model.rejected_by,
        rejected_on=model.rejected_on,
        rejection_reason=model.rejection_reason,
        published_by=model.published_by,
        published_on=model.published_on,
        published_entity_type_id=(
            Identifier(model.published_entity_type_id)
            if model.published_entity_type_id is not None
            else None
        ),
        published_relationship_type_id=(
            Identifier(model.published_relationship_type_id)
            if model.published_relationship_type_id is not None
            else None
        ),
    )
