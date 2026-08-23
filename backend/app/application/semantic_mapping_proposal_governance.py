"""Internal Gate L -- AI-Assisted Semantic Mapping Proposal Governance
(CDD-027 §11-§13, §17; AI-Assisted Semantic Mapping Candidate Discovery
Artifact Authorization §4.2, as corrected by the Human-Approver Attribution
Clarification and Remediation Report). Deterministically validates an
untrusted `CandidateSelection` and, only after every check passes,
materializes a `SemanticMapping` with `governance_status=PROPOSED` via the
existing, unmodified H1 `create()` method. Only an authenticated
`TrustedPrincipal` action may subsequently produce a **new**
`governance_status=APPROVED` row -- the `Proposed` row is never mutated.
Both `Proposed` and `Approved` rows use the fixed, repository-established
`BOOTSTRAP_SYSTEM_ENTITY_ID` attribution (never `principal.principal_id`,
which is not, and cannot safely be made, an `enterprise_entities`-FK-
compatible identity -- see the Clarification and Remediation Report).
Human approval authority is enforced entirely by requiring a real,
Gate-E-verified `TrustedPrincipal` and matching tenant; CDD-027 §21
authorizes no new scope/Keycloak configuration, so no additional scope
literal is introduced here. `reject()` performs no repository write of any
kind and does not introduce any new `GovernanceStatus` value."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.semantic_mapping_candidate_discovery import (
    CandidateDiscoveryContext,
    CandidateSelection,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.models.semantic_mapping import SemanticMappingORM
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepository
from app.infrastructure.persistence.source_field_repository import SourceFieldRepository


class SemanticMappingProposalGovernanceApplicationService:
    def __init__(
        self,
        *,
        session: Session,
        semantic_mapping_repository: SemanticMappingRepository,
        source_field_repository: SourceFieldRepository,
    ) -> None:
        self._session = session
        self._semantic_mapping_repository = semantic_mapping_repository
        self._source_field_repository = source_field_repository

    def materialize_proposal(
        self,
        *,
        tenant_id: str,
        candidate: CandidateSelection,
        context: CandidateDiscoveryContext,
        now: datetime | None = None,
    ) -> SemanticMapping:
        self._validate_candidate(tenant_id=tenant_id, candidate=candidate, context=context)

        proposal = SemanticMapping(
            semantic_mapping_id=Identifier(uuid4()),
            source_field_id=Identifier(candidate.source_field_id),
            information_element_requirement_id=Identifier(
                context.information_element_requirement_id
            ),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=now if now is not None else datetime.now(UTC),
        )
        self._semantic_mapping_repository.create(proposal)
        return proposal

    def approve(
        self,
        *,
        proposed: SemanticMapping,
        principal: TrustedPrincipal,
        now: datetime | None = None,
    ) -> SemanticMapping:
        self._authorize_approval(principal=principal, proposed=proposed)

        approved = SemanticMapping(
            semantic_mapping_id=Identifier(uuid4()),
            source_field_id=proposed.source_field_id,
            information_element_requirement_id=proposed.information_element_requirement_id,
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=now if now is not None else datetime.now(UTC),
        )
        self._semantic_mapping_repository.create(approved)
        return approved

    def reject(self, *, proposed: SemanticMapping, principal: TrustedPrincipal) -> None:
        if not isinstance(principal, TrustedPrincipal):
            raise ValidationException("A TrustedPrincipal is required to reject a proposal")
        if proposed.governance_status is not GovernanceStatus.PROPOSED:
            raise ValidationException("Only a Proposed SemanticMapping may be rejected")

    def _validate_candidate(
        self,
        *,
        tenant_id: str,
        candidate: CandidateSelection,
        context: CandidateDiscoveryContext,
    ) -> None:
        if not isinstance(candidate, CandidateSelection):
            raise ValidationException("Candidate selection must be a CandidateSelection")

        universe_ids = {cf.source_field_id for cf in context.candidate_source_fields}
        if candidate.source_field_id not in universe_ids:
            raise ValidationException(
                "Candidate source_field_id is not a member of the supplied candidate "
                f"universe: {candidate.source_field_id}"
            )

        source_field = self._source_field_repository.get_by_id(candidate.source_field_id)
        if source_field is None:
            raise ValidationException(f"SourceField does not exist: {candidate.source_field_id}")
        if source_field.lifecycle_state is not LifecycleState.ACTIVE:
            raise ValidationException(f"SourceField is not Active: {candidate.source_field_id}")
        if source_field.governance_status is not GovernanceStatus.APPROVED:
            raise ValidationException(
                f"SourceField is not an Approved governed field: {candidate.source_field_id}"
            )

        resolved_tenant_id = self._session.scalar(
            select(SourceObjectORM.tenant_id).where(
                SourceObjectORM.source_object_id == source_field.source_object_id.value
            )
        )
        if resolved_tenant_id is None or resolved_tenant_id != tenant_id:
            raise ValidationException(
                f"SourceField {candidate.source_field_id} is not owned by tenant {tenant_id!r}"
            )

        already_approved = self._session.scalar(
            select(SemanticMappingORM.semantic_mapping_id).where(
                SemanticMappingORM.source_field_id == candidate.source_field_id,
                SemanticMappingORM.governance_status == GovernanceStatus.APPROVED.value,
            )
        )
        if already_approved is not None:
            raise ValidationException(
                f"SourceField {candidate.source_field_id} already has an Approved SemanticMapping"
            )

    def _authorize_approval(
        self, *, principal: TrustedPrincipal, proposed: SemanticMapping
    ) -> None:
        if not isinstance(principal, TrustedPrincipal):
            raise ValidationException("A TrustedPrincipal is required to approve a proposal")
        if proposed.governance_status is not GovernanceStatus.PROPOSED:
            raise ValidationException("Only a Proposed SemanticMapping may be approved")

        resolved_tenant_id: str | None = self._session.scalar(
            select(SourceObjectORM.tenant_id)
            .join(
                SourceFieldORM,
                SourceFieldORM.source_object_id == SourceObjectORM.source_object_id,
            )
            .where(SourceFieldORM.source_field_id == proposed.source_field_id.value)
        )
        if resolved_tenant_id is None or resolved_tenant_id != principal.tenant_id:
            raise ValidationException(
                "Principal tenant does not match the Proposed mapping's own tenant"
            )
