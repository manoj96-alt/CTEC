from dataclasses import dataclass
from datetime import datetime

from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier


@dataclass(frozen=True, slots=True)
class SourceSystem:
    source_system_id: Identifier
    source_system_name: CanonicalName
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
            ("Source System ID", self.source_system_id),
            ("Created By", self.created_by),
            ("Modified By", self.modified_by),
            ("Previous Version", self.previous_version_id),
        ):
            if identifier_value is not None and not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.source_system_name, CanonicalName):
            raise ValidationException("Source System Name must be a Canonical Name")
        if len(self.source_system_name.value) > 200:
            raise ValidationException("Source System Name must not exceed 200 characters")
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
            if date_value is not None and date_value.tzinfo is None:
                raise ValidationException(f"{field_name} must include a timezone")
        if not isinstance(self.version_number, int) or isinstance(self.version_number, bool):
            raise ValidationException("Version Number must be an integer")
