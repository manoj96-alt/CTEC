"""Gate M -- Governed Visual Ontology Modeling routes (CDD-028; Gate M
Artifact Authorization v1.1 §10). Reuses Gate E's authentication (OIDC
bearer token -> TrustedPrincipal) and the exact scope-authorization pattern
of `app.api.entity_resolution.router` -- there is no separate mechanism
here. Six endpoints; no PUT/PATCH/DELETE. Only `publish` ever writes a
canonical ontology row -- `propose`/`approve`/`reject`/`get_proposal`/
`list_proposals` perform zero canonical writes, enforced by
`OntologyModelingProposalGovernanceApplicationService` (AA v1.1 §4.4), never
by this router. `publish` requires the `ontology-modeling:publish` scope
independently of `ontology-modeling:approve` -- a prior successful approve
call never implicitly authorizes a later publish call (AA v1.1 §7, §14)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.ontology_modeling.dependencies import (
    ontology_modeling_proposal_repository,
    ontology_modeling_service,
)
from app.api.ontology_modeling.schemas import (
    ProposalListResponse,
    ProposalResponse,
    ProposeRequest,
    RejectRequest,
)
from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.ontology_modeling_proposal_governance import (
    OntologyModelingProposalGovernanceApplicationService,
)
from app.core.dependency_container import Container
from app.domain.ontology_modeling.proposal import (
    OntologyChangeProposal,
    ProposalKind,
    ProposalStatus,
)
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.ontology_change_proposal_repository import (
    OntologyChangeProposalRepository,
)

router = APIRouter(prefix="/api/v1/ontology-modeling", tags=["ontology-modeling"])

_ENDPOINT_CLASSIFICATION = "ONTOLOGY_MODELING_API_V1"


@router.post("/proposals", response_model=ProposalResponse)
def propose(
    body: ProposeRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[
        OntologyModelingProposalGovernanceApplicationService, Depends(ontology_modeling_service)
    ],
) -> ProposalResponse:
    _authorize(authenticated, "ontology-modeling:propose", dependencies, correlation)
    try:
        if body.proposal_kind == ProposalKind.CREATE_CONCEPT:
            if body.entity_type_name is None:
                raise HTTPException(422, detail={"code": "ENTITY_TYPE_NAME_REQUIRED"})
            proposal = service.propose_concept(
                principal=authenticated,
                entity_type_name=body.entity_type_name,
                definition=body.definition,
            )
        elif body.proposal_kind == ProposalKind.CREATE_RELATIONSHIP:
            if (
                body.relationship_type_name is None
                or body.source_entity_type_id is None
                or body.target_entity_type_id is None
            ):
                raise HTTPException(422, detail={"code": "RELATIONSHIP_FIELDS_REQUIRED"})
            proposal = service.propose_relationship(
                principal=authenticated,
                relationship_type_name=body.relationship_type_name,
                source_entity_type_id=Identifier(body.source_entity_type_id),
                target_entity_type_id=Identifier(body.target_entity_type_id),
            )
        else:
            raise HTTPException(400, detail={"code": "INVALID_PROPOSAL_KIND"})
    except ValidationException as exc:
        raise HTTPException(
            422, detail={"code": "PROPOSAL_VALIDATION_FAILED", "message": str(exc)}
        ) from exc
    return _to_response(proposal)


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
def get_proposal(
    proposal_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    repository: Annotated[
        OntologyChangeProposalRepository, Depends(ontology_modeling_proposal_repository)
    ],
) -> ProposalResponse:
    _authorize_any(
        authenticated,
        ("ontology-modeling:read", "ontology-modeling:propose", "ontology-modeling:approve"),
        dependencies,
        correlation,
    )
    proposal = repository.get_by_id(proposal_id)
    if proposal is None:
        raise HTTPException(404, detail={"code": "PROPOSAL_NOT_FOUND"})
    return _to_response(proposal)


@router.get("/proposals", response_model=ProposalListResponse)
def list_proposals(
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    repository: Annotated[
        OntologyChangeProposalRepository, Depends(ontology_modeling_proposal_repository)
    ],
    status: Annotated[str | None, Query()] = None,
) -> ProposalListResponse:
    _authorize_any(
        authenticated,
        ("ontology-modeling:read", "ontology-modeling:propose", "ontology-modeling:approve"),
        dependencies,
        correlation,
    )
    status_filter: ProposalStatus | None = None
    if status is not None:
        try:
            status_filter = ProposalStatus(status)
        except ValueError as exc:
            raise HTTPException(400, detail={"code": "INVALID_STATUS_FILTER"}) from exc
    proposals = repository.list(status=status_filter)
    return ProposalListResponse(proposals=[_to_response(p) for p in proposals])


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalResponse)
def approve_proposal(
    proposal_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[
        OntologyModelingProposalGovernanceApplicationService, Depends(ontology_modeling_service)
    ],
    repository: Annotated[
        OntologyChangeProposalRepository, Depends(ontology_modeling_proposal_repository)
    ],
) -> ProposalResponse:
    _authorize(authenticated, "ontology-modeling:approve", dependencies, correlation)
    proposal = _load_or_404(repository, proposal_id)
    try:
        approved = service.approve(principal=authenticated, proposal=proposal)
    except ValidationException as exc:
        raise HTTPException(
            409, detail={"code": "INVALID_PROPOSAL_TRANSITION", "message": str(exc)}
        ) from exc
    return _to_response(approved)


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalResponse)
def reject_proposal(
    proposal_id: UUID,
    body: RejectRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[
        OntologyModelingProposalGovernanceApplicationService, Depends(ontology_modeling_service)
    ],
    repository: Annotated[
        OntologyChangeProposalRepository, Depends(ontology_modeling_proposal_repository)
    ],
) -> ProposalResponse:
    _authorize(authenticated, "ontology-modeling:approve", dependencies, correlation)
    proposal = _load_or_404(repository, proposal_id)
    try:
        rejected = service.reject(
            principal=authenticated,
            proposal=proposal,
            rejection_reason=body.rejection_reason,
        )
    except ValidationException as exc:
        raise HTTPException(
            409, detail={"code": "INVALID_PROPOSAL_TRANSITION", "message": str(exc)}
        ) from exc
    return _to_response(rejected)


@router.post("/proposals/{proposal_id}/publish", response_model=ProposalResponse)
def publish_proposal(
    proposal_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[
        OntologyModelingProposalGovernanceApplicationService, Depends(ontology_modeling_service)
    ],
    repository: Annotated[
        OntologyChangeProposalRepository, Depends(ontology_modeling_proposal_repository)
    ],
) -> ProposalResponse:
    # Independently checked -- never implied by ontology-modeling:approve.
    _authorize(authenticated, "ontology-modeling:publish", dependencies, correlation)
    proposal = _load_or_404(repository, proposal_id)
    try:
        published = service.publish(principal=authenticated, proposal=proposal)
    except ValidationException as exc:
        raise HTTPException(409, detail={"code": "PUBLISH_FAILED", "message": str(exc)}) from exc
    return _to_response(published)


def _load_or_404(
    repository: OntologyChangeProposalRepository, proposal_id: UUID
) -> OntologyChangeProposal:
    proposal = repository.get_by_id(proposal_id)
    if proposal is None:
        raise HTTPException(404, detail={"code": "PROPOSAL_NOT_FOUND"})
    return proposal


def _to_response(proposal: OntologyChangeProposal) -> ProposalResponse:
    return ProposalResponse(
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


def _authorize(
    authenticated: TrustedPrincipal,
    scope: str,
    dependencies: Container,
    correlation: UUID,
) -> None:
    if scope in authenticated.scopes:
        return
    _record_denied(dependencies, correlation, authenticated)
    raise HTTPException(403, detail={"code": "AUTHORIZATION_SCOPE_REQUIRED"})


def _authorize_any(
    authenticated: TrustedPrincipal,
    scopes: tuple[str, ...],
    dependencies: Container,
    correlation: UUID,
) -> None:
    if any(scope in authenticated.scopes for scope in scopes):
        return
    _record_denied(dependencies, correlation, authenticated)
    raise HTTPException(403, detail={"code": "AUTHORIZATION_SCOPE_REQUIRED"})


def _record_denied(
    dependencies: Container, correlation: UUID, authenticated: TrustedPrincipal
) -> None:
    audit: SecurityAuditService | None = dependencies.security_audit
    if audit is not None:
        audit.record(
            operation="AUTHORIZE_API_OPERATION",
            category="AUTHORIZATION",
            outcome="DENIED",
            code="AUTHORIZATION_SCOPE_REQUIRED",
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
