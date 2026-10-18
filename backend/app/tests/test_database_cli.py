"""CDD-087 §28 CREATE 3: unit-level tests for golden-demo-restore's
five-check safety predicate's pure-logic checks (opt-in, environment,
host) and for the `environment` Literal widening (CDD-087 §12) -- no live
PostgreSQL required, no database ever touched. Real-database checks
(migration head, foreign-tenant absence, the scoped delete, reseed,
repeatability, transactionality, and the three new demo-verify assertions)
live in test_database_cli_postgres.py.

Establishes this file's own first test-naming precedent for
database_cli.py, which had no test file before this program (CDD-087
§28 CREATE 3)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.infrastructure.persistence.database_cli import (
    GoldenDemoRestoreNotAllowedError,
    _assert_golden_demo_restore_allowed,
)


@pytest.fixture(autouse=True)
def _clear_golden_restore_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Every test starts from a clean slate: none of golden-demo-restore's
    own environment variables set, settings cache cleared before and
    after so no test's monkeypatched CTEC_ENVIRONMENT leaks into another
    test via lru_cache."""
    monkeypatch.delenv("CTEC_GOLDEN_DEMO_RESTORE_ALLOWED", raising=False)
    monkeypatch.delenv("CTEC_GOLDEN_RESTORE_EXPECTED_HOST", raising=False)
    monkeypatch.delenv("CTEC_ENVIRONMENT", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ----------------------------------------------------------------------
# Check 1 -- explicit opt-in.
# ----------------------------------------------------------------------


def test_check1_opt_in_absent_refuses() -> None:
    with pytest.raises(GoldenDemoRestoreNotAllowedError, match="CTEC_GOLDEN_DEMO_RESTORE_ALLOWED"):
        _assert_golden_demo_restore_allowed("postgresql://x/y", MagicMock())


def test_check1_opt_in_false_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CTEC_GOLDEN_DEMO_RESTORE_ALLOWED", "false")
    with pytest.raises(GoldenDemoRestoreNotAllowedError, match="CTEC_GOLDEN_DEMO_RESTORE_ALLOWED"):
        _assert_golden_demo_restore_allowed("postgresql://x/y", MagicMock())


# ----------------------------------------------------------------------
# Check 2 -- application-declared environment.
# ----------------------------------------------------------------------


def test_check2_wrong_environment_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CTEC_GOLDEN_DEMO_RESTORE_ALLOWED", "true")
    monkeypatch.setenv("CTEC_ENVIRONMENT", "development")
    get_settings.cache_clear()
    with pytest.raises(GoldenDemoRestoreNotAllowedError, match="not 'demo'"):
        _assert_golden_demo_restore_allowed("postgresql://x/y", MagicMock())


# ----------------------------------------------------------------------
# Check 3 -- exact database host identity.
# ----------------------------------------------------------------------


def test_check3_expected_host_unset_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CTEC_GOLDEN_DEMO_RESTORE_ALLOWED", "true")
    monkeypatch.setenv("CTEC_ENVIRONMENT", "demo")
    get_settings.cache_clear()
    with pytest.raises(GoldenDemoRestoreNotAllowedError, match="CTEC_GOLDEN_RESTORE_EXPECTED_HOST"):
        _assert_golden_demo_restore_allowed("postgresql://user:pw@somehost/db", MagicMock())


def test_check3_host_mismatch_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CTEC_GOLDEN_DEMO_RESTORE_ALLOWED", "true")
    monkeypatch.setenv("CTEC_ENVIRONMENT", "demo")
    monkeypatch.setenv(
        "CTEC_GOLDEN_RESTORE_EXPECTED_HOST", "noetva-demo-eus2-pg.postgres.database.azure.com"
    )
    get_settings.cache_clear()
    with pytest.raises(GoldenDemoRestoreNotAllowedError, match="does not match"):
        _assert_golden_demo_restore_allowed("postgresql://user:pw@wronghost/db", MagicMock())


# ----------------------------------------------------------------------
# Ordering -- Checks 1-3 must never touch the session (defense against a
# future refactor accidentally reordering the predicate past the
# database-requiring checks).
# ----------------------------------------------------------------------


def test_checks_1_through_3_never_touch_the_session() -> None:
    session = MagicMock()
    with pytest.raises(GoldenDemoRestoreNotAllowedError):
        _assert_golden_demo_restore_allowed("postgresql://x/y", session)
    session.execute.assert_not_called()


# ----------------------------------------------------------------------
# CDD-087 §12 -- environment Literal widening. No branching behavior is
# introduced by any of the new values; this only proves the type accepts
# them (and still rejects everything it always rejected).
# ----------------------------------------------------------------------


@pytest.mark.parametrize("value", ["development", "test", "staging", "demo", "production"])
def test_environment_literal_accepts_every_governed_value(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("CTEC_ENVIRONMENT", value)
    get_settings.cache_clear()
    assert get_settings().environment == value


def test_environment_literal_still_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CTEC_ENVIRONMENT", "not-a-real-environment")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()
