from dataclasses import dataclass

from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier


@dataclass(frozen=True, slots=True)
class EnterpriseType:
    enterprise_type_id: Identifier
    type_name: CanonicalName

    def __post_init__(self) -> None:
        if not isinstance(self.enterprise_type_id, Identifier):
            raise ValidationException("Enterprise Type ID must be an Identifier")
        if not isinstance(self.type_name, CanonicalName):
            raise ValidationException("Type Name must be a Canonical Name")
        if len(self.type_name.value) > 100:
            raise ValidationException("Type Name must not exceed 100 characters")
