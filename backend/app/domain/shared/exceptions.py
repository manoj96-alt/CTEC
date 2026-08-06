class DomainException(Exception):
    """Base exception for the pure domain model."""


class ValidationException(DomainException):
    """Raised when canonical structure is invalid."""
