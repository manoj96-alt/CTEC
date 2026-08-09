"""Integrity-first recovery selection without business interpretation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

from app.integration.contracts import AuthorityContext

STAGES = ("ERM", "SRM", "ASM", "KRM", "DRM", "GRM")
_VALIDATED: Final[object] = object()


@dataclass(frozen=True, slots=True)
class RecoveryCheckpoint:
    stage_id: UUID
    stage_name: str
    stage_ordinal: int
    committed: bool
    integrity_valid: bool
    side_effect_certain: bool


def next_stage(checkpoints: tuple[RecoveryCheckpoint, ...]) -> int:
    ordered = sorted(checkpoints, key=lambda item: item.stage_ordinal)
    for expected, item in enumerate(ordered):
        if item.stage_ordinal != expected or item.stage_name != STAGES[expected]:
            raise ValueError("Checkpoint order is invalid")
        if not item.side_effect_certain:
            raise RuntimeError("Uncertain side effect prohibits automatic recovery")
        if not item.committed or not item.integrity_valid:
            return expected
    return len(ordered)


@dataclass(frozen=True, slots=True)
class ValidatedRecoveryInvocation:
    execution_identifier: UUID
    logical_execution_identifier: UUID
    protocol_version: str
    correlation_identifier: UUID
    request_identifier: UUID
    session_identifier: UUID
    request_classification: str
    opaque_payload: bytes
    authority_context: AuthorityContext
    admitted_at: datetime
    resume_stage_ordinal: int
    recovery_identifier: UUID
    _marker: object

    @property
    def validated(self) -> bool:
        return self._marker is _VALIDATED


def validated_recovery_invocation(
    *,
    execution_identifier: UUID,
    logical_execution_identifier: UUID,
    protocol_version: str,
    correlation_identifier: UUID,
    request_identifier: UUID,
    session_identifier: UUID,
    request_classification: str,
    opaque_payload: bytes,
    authority_context: AuthorityContext,
    admitted_at: datetime,
    resume_stage_ordinal: int,
    recovery_identifier: UUID,
) -> ValidatedRecoveryInvocation:
    if resume_stage_ordinal not in range(len(STAGES)):
        raise ValueError("Recovery resume stage is invalid")
    return ValidatedRecoveryInvocation(
        execution_identifier,
        logical_execution_identifier,
        protocol_version,
        correlation_identifier,
        request_identifier,
        session_identifier,
        request_classification,
        opaque_payload,
        authority_context,
        admitted_at,
        resume_stage_ordinal,
        recovery_identifier,
        _VALIDATED,
    )
