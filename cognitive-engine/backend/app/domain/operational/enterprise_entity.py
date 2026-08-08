from dataclasses import dataclass
from datetime import datetime

from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier


@dataclass(frozen=True, slots=True)
class EnterpriseEntity:
    enterprise_entity_id: Identifier
    enterprise_entity_name: CanonicalName
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
    entity_type_id: Identifier
    business_domain_id: Identifier

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Enterprise Entity ID", self.enterprise_entity_id),
            ("Created By", self.created_by),
            ("Modified By", self.modified_by),
            ("Previous Version", self.previous_version_id),
            ("Entity Type", self.entity_type_id),
            ("Business Domain", self.business_domain_id),
        ):
            if identifier_value is not None and not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.enterprise_entity_name, CanonicalName):
            raise ValidationException("Enterprise Entity Name must be a Canonical Name")
        if len(self.enterprise_entity_name.value) > 200:
            raise ValidationException("Enterprise Entity Name must not exceed 200 characters")
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
