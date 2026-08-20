"""Repository for `SemanticMapping` (Gate H H1; CDD-019 §8, §11, §16, H1
Source Field / Semantic Mapping Artifact Authorization companion; Gate H H2;
CDD-019 §14, §16, H2 Semantic Mapping Resolution Artifact Authorization).

Exposes exactly three members on the `Protocol`: `create(...)`,
`get_by_id(...)`, and `get_approved_by_information_element_requirement(...)`.
`create()` internally enforces CDD-019 §11's two symmetric Approved-mapping
uniqueness rules before insert -- (a) no existing Approved row shares the new
row's `source_field_id`; (b) no existing Approved row shares the new row's
`information_element_requirement_id` within the same tenant (resolved via a
join through `source_field_id -> source_object_id -> tenant_id`) -- raising
`ValidationException` on either violation.

BINDING (H1 companion, "Repository Protocol firewall"): the ambiguity-check
logic inside `create()` is a private implementation detail of `create()`
alone -- never a named public method, never independently callable, never
exposed on the `Protocol`.

`get_approved_by_information_element_requirement(...)` (H2 companion) is the
sole governed resolution query this module authorizes: for a given tenant
and `information_element_requirement_id`, resolve the Approved
`SemanticMapping` (if any) and return a `SemanticMappingResolution` carrying
enough provenance to identify the resolved `SourceField`
(`source_field_id`, `source_object_id`, `source_system_id` via join) and the
`SemanticMapping` row's own identity/audit metadata. No `find`, `search`,
arbitrary status filter, list-all, or arbitrary-combination lookup method is
authorized -- that capability remains exclusively out of scope."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.models.semantic_mapping import SemanticMappingORM
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM


@dataclass(frozen=True, slots=True)
class SemanticMappingResolution:
    """H2 resolution result (CDD-019 §14, H2 companion) -- exactly the nine
    authorized fields: the resolved `SourceField`'s provenance
    (`source_field_id`, `source_object_id`, `source_system_id`) plus the
    resolved `SemanticMapping`'s own identity (`semantic_mapping_id`,
    `information_element_requirement_id`) and audit metadata (`created_by`,
    `created_on`, `modified_by`, `modified_on`). No `governance_status`
    field: every result is Approved by construction of the query that
    produces it."""

    semantic_mapping_id: UUID
    source_field_id: UUID
    source_object_id: UUID
    source_system_id: UUID
    information_element_requirement_id: UUID
    created_by: UUID
    created_on: datetime
    modified_by: UUID | None
    modified_on: datetime | None


class SemanticMappingRepository(Protocol):
    def create(self, semantic_mapping: SemanticMapping) -> None: ...

    def get_by_id(self, semantic_mapping_id: UUID) -> SemanticMapping | None: ...

    def get_approved_by_information_element_requirement(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> SemanticMappingResolution | None: ...


class SemanticMappingRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, semantic_mapping: SemanticMapping) -> None:
        if semantic_mapping.governance_status is GovernanceStatus.APPROVED:
            self._raise_if_ambiguous(semantic_mapping)
        self.session.add(
            SemanticMappingORM(
                semantic_mapping_id=semantic_mapping.semantic_mapping_id.value,
                source_field_id=semantic_mapping.source_field_id.value,
                information_element_requirement_id=(
                    semantic_mapping.information_element_requirement_id.value
                ),
                lifecycle_state=semantic_mapping.lifecycle_state.value,
                governance_status=semantic_mapping.governance_status.value,
                created_by=semantic_mapping.created_by.value,
                created_on=semantic_mapping.created_on,
                modified_by=(
                    semantic_mapping.modified_by.value
                    if semantic_mapping.modified_by is not None
                    else None
                ),
                modified_on=semantic_mapping.modified_on,
            )
        )

    def get_by_id(self, semantic_mapping_id: UUID) -> SemanticMapping | None:
        model = self.session.get(SemanticMappingORM, semantic_mapping_id)
        if model is None:
            return None
        return SemanticMapping(
            semantic_mapping_id=Identifier(model.semantic_mapping_id),
            source_field_id=Identifier(model.source_field_id),
            information_element_requirement_id=Identifier(model.information_element_requirement_id),
            lifecycle_state=LifecycleState(model.lifecycle_state),
            governance_status=GovernanceStatus(model.governance_status),
            created_by=Identifier(model.created_by),
            created_on=model.created_on,
            modified_by=Identifier(model.modified_by) if model.modified_by is not None else None,
            modified_on=model.modified_on,
        )

    def get_approved_by_information_element_requirement(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> SemanticMappingResolution | None:
        """CDD-019 §14, H2 companion: for a given tenant and
        `information_element_requirement_id`, resolve the Approved
        `SemanticMapping` (if any). Tenant is resolved exclusively via the
        join below -- never a stored column on either `semantic_mappings` or
        `source_fields`. Zero matches -> `None` (a valid, successful
        outcome, not a failure). More than one match is a defensive-only
        path -- H1's `create()` already makes it structurally unreachable --
        that raises rather than silently selecting a row."""
        rows = self.session.execute(
            select(SemanticMappingORM, SourceFieldORM, SourceObjectORM)
            .join(
                SourceFieldORM,
                SourceFieldORM.source_field_id == SemanticMappingORM.source_field_id,
            )
            .join(
                SourceObjectORM,
                SourceObjectORM.source_object_id == SourceFieldORM.source_object_id,
            )
            .where(
                SemanticMappingORM.information_element_requirement_id
                == information_element_requirement_id,
                SemanticMappingORM.governance_status == GovernanceStatus.APPROVED.value,
                SourceObjectORM.tenant_id == tenant_id,
            )
        ).all()

        if not rows:
            return None
        if len(rows) > 1:
            matched_ids = [mapping.semantic_mapping_id for mapping, _, _ in rows]
            raise ValidationException(
                "Ambiguous Approved SemanticMapping resolution for "
                f"information_element_requirement_id {information_element_requirement_id} "
                f"within tenant {tenant_id}: {matched_ids}"
            )

        mapping, field, source_object = rows[0]
        return SemanticMappingResolution(
            semantic_mapping_id=mapping.semantic_mapping_id,
            source_field_id=field.source_field_id,
            source_object_id=source_object.source_object_id,
            source_system_id=source_object.source_system_id,
            information_element_requirement_id=mapping.information_element_requirement_id,
            created_by=mapping.created_by,
            created_on=mapping.created_on,
            modified_by=mapping.modified_by,
            modified_on=mapping.modified_on,
        )

    def _raise_if_ambiguous(self, semantic_mapping: SemanticMapping) -> None:
        """Private write-time integrity guard for CDD-019 §11 -- not a
        resolution query. Invalid FK references (a `source_field_id` that
        does not exist) are deliberately left to the database's own FK
        constraint to reject as `IntegrityError` (CDD-019 §23); this method
        only ever raises for an ambiguous *Approved* pairing."""
        source_field_id = semantic_mapping.source_field_id.value
        existing_for_field = self.session.scalars(
            select(SemanticMappingORM.semantic_mapping_id).where(
                SemanticMappingORM.source_field_id == source_field_id,
                SemanticMappingORM.governance_status == GovernanceStatus.APPROVED.value,
            )
        ).first()
        if existing_for_field is not None:
            raise ValidationException(
                f"An Approved SemanticMapping already exists for source_field_id: {source_field_id}"
            )

        tenant_id = self.session.scalar(
            select(SourceObjectORM.tenant_id)
            .join(
                SourceFieldORM,
                SourceFieldORM.source_object_id == SourceObjectORM.source_object_id,
            )
            .where(SourceFieldORM.source_field_id == source_field_id)
        )
        if tenant_id is None:
            # source_field_id does not resolve to a real SourceField -- not
            # this method's concern; the FK constraint rejects it on insert.
            return

        information_element_requirement_id = (
            semantic_mapping.information_element_requirement_id.value
        )
        # The source-side rule above is backed by a durable database partial
        # unique index (models/semantic_mapping.py), so a concurrent race
        # there can never persist ambiguity -- the losing transaction's
        # commit fails regardless of what this pre-check saw. The
        # target-side rule has no such database backstop (CDD-019 §11:
        # tenant is join-derived, not a stored column), so without
        # serialization here, two concurrent create() calls for the same
        # (information_element_requirement_id, tenant) could both pass this
        # check before either commits. A PostgreSQL transaction-scoped
        # advisory lock, keyed on that same pair, forces the second
        # concurrent caller to wait until the first's transaction ends
        # (commit or rollback) before its own SELECT below runs, so it
        # always sees the first caller's already-committed row.
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:tenant_id), hashtext(:element_id))"),
            {
                "tenant_id": tenant_id,
                "element_id": str(information_element_requirement_id),
            },
        )
        existing_for_element = self.session.scalars(
            select(SemanticMappingORM.semantic_mapping_id)
            .join(
                SourceFieldORM,
                SourceFieldORM.source_field_id == SemanticMappingORM.source_field_id,
            )
            .join(
                SourceObjectORM,
                SourceObjectORM.source_object_id == SourceFieldORM.source_object_id,
            )
            .where(
                SemanticMappingORM.information_element_requirement_id
                == information_element_requirement_id,
                SemanticMappingORM.governance_status == GovernanceStatus.APPROVED.value,
                SourceObjectORM.tenant_id == tenant_id,
            )
        ).first()
        if existing_for_element is not None:
            raise ValidationException(
                "An Approved SemanticMapping already exists for "
                f"information_element_requirement_id {information_element_requirement_id} "
                f"within tenant {tenant_id}"
            )
