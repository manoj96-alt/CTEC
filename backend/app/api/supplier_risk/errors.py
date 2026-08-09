"""Safe external error contract."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ApiProblem(Exception):
    status_code: int
    code: str
    correlation_id: UUID
    retryable: bool = False
    message: str = "Request could not be completed"
