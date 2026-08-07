from dataclasses import dataclass

from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier, ReferenceCode


@dataclass(frozen=True, slots=True)
class Country:
    country_id: Identifier
    country_name: CanonicalName
    iso2_code: ReferenceCode
    iso3_code: ReferenceCode

    def __post_init__(self) -> None:
        if not isinstance(self.country_id, Identifier):
            raise ValidationException("Country ID must be an Identifier")
        if not isinstance(self.country_name, CanonicalName):
            raise ValidationException("Country Name must be a Canonical Name")
        if not isinstance(self.iso2_code, ReferenceCode):
            raise ValidationException("ISO2 must be a Reference Code")
        if not isinstance(self.iso3_code, ReferenceCode):
            raise ValidationException("ISO3 must be a Reference Code")
        if len(self.country_name.value) > 100:
            raise ValidationException("Country Name must not exceed 100 characters")
        if len(self.iso2_code.value) != 2:
            raise ValidationException("ISO2 must contain exactly 2 characters")
        if len(self.iso3_code.value) != 3:
            raise ValidationException("ISO3 must contain exactly 3 characters")
