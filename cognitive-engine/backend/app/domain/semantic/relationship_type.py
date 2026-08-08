from dataclasses import dataclass
from datetime import datetime

from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier


@dataclass(frozen=True, slots=True)
class RelationshipType:
    relationship_type_id: Identifier
    relationship_type_name: CanonicalName
    lifecycle_state: LifecycleState
    effective_from: datetime
    effective_to: datetime | None
    governance_status: GovernanceStatus
    created_by: Identifier
    created_on: datetime
    modified_by: Identifier | None
    modified_on: datetime | None
    version_number: int
    previous_version_id: Identifier | None

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Relationship Type ID", self.relationship_type_id),
            ("Created By", self.created_by),
            ("Modified By", self.modified_by),
            ("Previous Version", self.previous_version_id),
        ):
            if identifier_value is not None and not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.relationship_type_name, CanonicalName):
            raise ValidationException("Relationship Type Name must be a Canonical Name")
        if not isinstance(self.lifecycle_state, LifecycleState):
            raise ValidationException("Lifecycle State must be a Lifecycle State")
        if not isinstance(self.governance_status, GovernanceStatus):
            raise ValidationException("Governance Status must be a Governance Status")
        for field_name, date_value in (
            ("Effective From", self.effective_from),
            ("Effective To", self.effective_to),
            ("Created On", self.created_on),
            ("Modified On", self.modified_on),
        ):
            if date_value is not None and not isinstance(date_value, datetime):
                raise ValidationException(f"{field_name} must be a datetime")
        if len(self.relationship_type_name.value) > 200:
            raise ValidationException("Relationship Type Name must not exceed 200 characters")
        if self.effective_from.tzinfo is None:
            raise ValidationException("Effective From must include a timezone")
        if self.created_on.tzinfo is None:
            raise ValidationException("Created On must include a timezone")
        if self.effective_to is not None and self.effective_to.tzinfo is None:
            raise ValidationException("Effective To must include a timezone")
        if self.modified_on is not None and self.modified_on.tzinfo is None:
            raise ValidationException("Modified On must include a timezone")
        if not isinstance(self.version_number, int) or isinstance(self.version_number, bool):
            raise ValidationException("Version Number must be an integer")
