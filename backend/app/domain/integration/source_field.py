"""Domain model for a physical source field (Gate H H1; CDD-019 §7, H1
Source Field / Semantic Mapping Artifact Authorization). Identifies a field
within an already-governed `SourceObject` -- the smallest granularity
`SourceSystem`/`SourceObject` do not already reach. Carries no `tenant_id`
(tenant is resolved transitively through `source_object_id`) and no
semantic/type/vocabulary information of any kind."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier


@dataclass(frozen=True, slots=True)
class SourceField:
    source_field_id: Identifier
    source_object_id: Identifier
    field_label: CanonicalName
    lifecycle_state: LifecycleState
    governance_status: GovernanceStatus
    created_by: Identifier
    created_on: datetime
    modified_by: Identifier | None = None
    modified_on: datetime | None = None

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Source Field ID", self.source_field_id),
            ("Source Object", self.source_object_id),
            ("Created By", self.created_by),
            ("Modified By", self.modified_by),
        ):
            if identifier_value is not None and not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.field_label, CanonicalName):
            raise ValidationException("Field Label must be a Canonical Name")
        if len(self.field_label.value) > 200:
            raise ValidationException("Field Label must not exceed 200 characters")
        if not isinstance(self.lifecycle_state, LifecycleState):
            raise ValidationException("Lifecycle State must be a Lifecycle State")
        if not isinstance(self.governance_status, GovernanceStatus):
            raise ValidationException("Governance Status must be a Governance Status")
        if self.created_on.tzinfo is None:
            raise ValidationException("Created On must include a timezone")
        if self.modified_on is not None and self.modified_on.tzinfo is None:
            raise ValidationException("Modified On must include a timezone")
