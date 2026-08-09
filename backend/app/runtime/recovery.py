"""Integrity-first recovery selection without business interpretation."""

from dataclasses import dataclass
from uuid import UUID

STAGES = ("ERM", "SRM", "ASM", "KRM", "DRM", "GRM")


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
