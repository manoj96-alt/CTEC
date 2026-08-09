from uuid import uuid4

import pytest

from app.runtime.recovery import RecoveryCheckpoint, next_stage


def checkpoint(
    name: str, ordinal: int, *, committed: bool = True, certain: bool = True
) -> RecoveryCheckpoint:
    return RecoveryCheckpoint(uuid4(), name, ordinal, committed, True, certain)


def test_recovery_resumes_after_last_committed_stage() -> None:
    assert next_stage((checkpoint("ERM", 0), checkpoint("SRM", 1, committed=False))) == 1


def test_uncertain_side_effect_blocks_automatic_replay() -> None:
    with pytest.raises(RuntimeError, match="Uncertain"):
        next_stage((checkpoint("ERM", 0, certain=False),))
