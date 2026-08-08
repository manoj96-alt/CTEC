from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.exceptions import ValidationException


@dataclass(frozen=True, slots=True)
class Identifier:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ValidationException("Identifier must be a UUID")


@dataclass(frozen=True, slots=True)
class CanonicalName:
    value: str

    def __post_init__(self) -> None:
        _validate_text(self.value, "Canonical Name")


@dataclass(frozen=True, slots=True)
class BusinessName:
    value: str

    def __post_init__(self) -> None:
        _validate_text(self.value, "Business Name")


@dataclass(frozen=True, slots=True)
class Description:
    value: str

    def __post_init__(self) -> None:
        _validate_text(self.value, "Description")


@dataclass(frozen=True, slots=True)
class ReferenceCode:
    value: str

    def __post_init__(self) -> None:
        _validate_text(self.value, "Reference Code")


def _validate_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationException(f"{name} must be non-empty text")
