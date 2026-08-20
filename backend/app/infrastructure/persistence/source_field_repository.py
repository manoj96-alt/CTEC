"""Repository for `SourceField` (Gate H H1; CDD-019 §7, §16, H1 Source Field
/ Semantic Mapping Artifact Authorization companion). Minimal repository:
`create(...)` and `get_by_id(...)` only -- `get_by_id` is an internal read
needed by tests only, matching `BlueprintRepository.get_by_id`'s identical
G2 precedent. No `get_by_object_id`, no "list all," no resolution-shaped or
criteria-based query method of any kind."""

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.integration import SourceField
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.models.source_field import SourceFieldORM


class SourceFieldRepository(Protocol):
    def create(self, source_field: SourceField) -> None: ...

    def get_by_id(self, source_field_id: UUID) -> SourceField | None: ...


class SourceFieldRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, source_field: SourceField) -> None:
        self.session.add(
            SourceFieldORM(
                source_field_id=source_field.source_field_id.value,
                source_object_id=source_field.source_object_id.value,
                field_label=source_field.field_label.value,
                lifecycle_state=source_field.lifecycle_state.value,
                governance_status=source_field.governance_status.value,
                created_by=source_field.created_by.value,
                created_on=source_field.created_on,
                modified_by=(
                    source_field.modified_by.value if source_field.modified_by is not None else None
                ),
                modified_on=source_field.modified_on,
            )
        )

    def get_by_id(self, source_field_id: UUID) -> SourceField | None:
        model = self.session.get(SourceFieldORM, source_field_id)
        if model is None:
            return None
        return SourceField(
            source_field_id=Identifier(model.source_field_id),
            source_object_id=Identifier(model.source_object_id),
            field_label=CanonicalName(model.field_label),
            lifecycle_state=LifecycleState(model.lifecycle_state),
            governance_status=GovernanceStatus(model.governance_status),
            created_by=Identifier(model.created_by),
            created_on=model.created_on,
            modified_by=Identifier(model.modified_by) if model.modified_by is not None else None,
            modified_on=model.modified_on,
        )
