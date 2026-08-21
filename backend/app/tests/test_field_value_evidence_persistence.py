"""Unit tests for `FieldValueEvidence` (CDD-022 §6-§12, §25; Field-Value
Evidence Artifact Authorization). Domain construction, empty/whitespace
value semantics, and the collision-safe deterministic-identity derivation
-- no PostgreSQL dependency, exercising the real production domain code
directly (no duplicate test-only identity helper).
"""

import dataclasses
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.integration.field_value_evidence import (
    FieldValueEvidence,
    derive_field_value_evidence_id,
)
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _source_field_id() -> Identifier:
    return Identifier(uuid4())


# ---------------------------------------------------------------------------
# Domain construction
# ---------------------------------------------------------------------------


def test_valid_construction_with_non_empty_representation() -> None:
    evidence = FieldValueEvidence.new(
        source_field_id=_source_field_id(),
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
    )
    assert evidence.observed_representation == "Acme Taiwan Ltd"


def test_empty_observed_representation_is_accepted() -> None:
    evidence = FieldValueEvidence.new(
        source_field_id=_source_field_id(),
        source_record_reference="100045",
        observed_representation="",
        observed_at=NOW,
        received_at=NOW,
    )
    assert evidence.observed_representation == ""


def test_whitespace_only_observed_representation_is_preserved_unmodified() -> None:
    evidence = FieldValueEvidence.new(
        source_field_id=_source_field_id(),
        source_record_reference="100045",
        observed_representation="   ",
        observed_at=NOW,
        received_at=NOW,
    )
    assert evidence.observed_representation == "   "


def test_none_observed_representation_is_rejected() -> None:
    with pytest.raises(ValidationException, match="must be text"):
        FieldValueEvidence.new(
            source_field_id=_source_field_id(),
            source_record_reference="100045",
            observed_representation=None,  # type: ignore[arg-type]
            observed_at=NOW,
            received_at=NOW,
        )


def test_naive_observed_at_is_rejected() -> None:
    with pytest.raises(ValidationException, match="Observed At must be a timezone-aware datetime"):
        FieldValueEvidence.new(
            source_field_id=_source_field_id(),
            source_record_reference="100045",
            observed_representation="Acme Taiwan Ltd",
            observed_at=datetime(2026, 1, 1),  # noqa: DTZ001
            received_at=NOW,
        )


def test_naive_received_at_is_rejected() -> None:
    with pytest.raises(ValidationException, match="Received At must be a timezone-aware datetime"):
        FieldValueEvidence.new(
            source_field_id=_source_field_id(),
            source_record_reference="100045",
            observed_representation="Acme Taiwan Ltd",
            observed_at=NOW,
            received_at=datetime(2026, 1, 1),  # noqa: DTZ001
        )


def test_evidence_reference_none_is_accepted() -> None:
    evidence = FieldValueEvidence.new(
        source_field_id=_source_field_id(),
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
    )
    assert evidence.evidence_reference is None


def test_field_value_evidence_is_immutable() -> None:
    evidence = FieldValueEvidence.new(
        source_field_id=_source_field_id(),
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.observed_representation = "Acme Taiwan LLC"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Identity / collision safety
# ---------------------------------------------------------------------------


def test_identical_semantic_inputs_yield_identical_id() -> None:
    field_id = _source_field_id()
    first = FieldValueEvidence.new(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
    )
    second = FieldValueEvidence.new(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
    )
    assert first.field_value_evidence_id == second.field_value_evidence_id


def test_delimiter_shift_collision_counter_example_a_does_not_collide() -> None:
    field_id = _source_field_id().value
    id_a = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045:extra",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
    )
    id_b = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="extra:Acme Taiwan Ltd",
        observed_at=NOW,
    )
    assert id_a != id_b


def test_delimiter_shift_collision_counter_example_b_does_not_collide() -> None:
    field_id = _source_field_id().value
    id_a = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="a:b",
        observed_representation="c",
        observed_at=NOW,
    )
    id_b = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="a",
        observed_representation="b:c",
        observed_at=NOW,
    )
    assert id_a != id_b


def test_empty_representation_differs_from_any_non_empty_value() -> None:
    field_id = _source_field_id().value
    id_empty = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="",
        observed_at=NOW,
    )
    id_non_empty = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="x",
        observed_at=NOW,
    )
    assert id_empty != id_non_empty


def test_whitespace_differs_from_empty() -> None:
    field_id = _source_field_id().value
    id_whitespace = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation=" ",
        observed_at=NOW,
    )
    id_empty = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="",
        observed_at=NOW,
    )
    assert id_whitespace != id_empty


def test_multibyte_utf8_byte_length_is_deterministic_and_distinct_from_ascii() -> None:
    field_id = _source_field_id().value
    # "Ácme" is 4 characters but 5 UTF-8 bytes (the accented A is 2 bytes);
    # "Adcme" is 5 characters and 5 ASCII bytes. If byte length governed the
    # encoding incorrectly via character count instead, these could collide
    # in principle; asserting inequality proves byte length is what is used
    # and that it is computed correctly per string, not merely present.
    id_multibyte = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Ácme",
        observed_at=NOW,
    )
    id_ascii = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Adcme",
        observed_at=NOW,
    )
    assert id_multibyte != id_ascii
    # Determinism: repeated computation over the same multibyte input agrees.
    id_multibyte_again = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Ácme",
        observed_at=NOW,
    )
    assert id_multibyte == id_multibyte_again


def test_changing_only_source_field_id_yields_different_id() -> None:
    id_a = derive_field_value_evidence_id(
        source_field_id=uuid4(),
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
    )
    id_b = derive_field_value_evidence_id(
        source_field_id=uuid4(),
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
    )
    assert id_a != id_b


def test_changing_only_observed_at_yields_different_id() -> None:
    field_id = _source_field_id().value
    id_a = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
    )
    id_b = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW + timedelta(days=1),
    )
    assert id_a != id_b


def test_changing_only_source_record_reference_yields_different_id() -> None:
    field_id = _source_field_id().value
    id_a = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
    )
    id_b = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100046",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
    )
    assert id_a != id_b


def test_case_difference_yields_different_id() -> None:
    field_id = _source_field_id().value
    id_lower = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme",
        observed_at=NOW,
    )
    id_upper = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="ACME",
        observed_at=NOW,
    )
    assert id_lower != id_upper


def test_same_instant_different_utc_offset_yields_same_id() -> None:
    field_id = _source_field_id().value
    western = datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone(timedelta(hours=-7)))
    utc = datetime(2026, 8, 20, 17, 0, 0, tzinfo=UTC)
    id_western = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=western,
    )
    id_utc = derive_field_value_evidence_id(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=utc,
    )
    assert id_western == id_utc


def test_received_at_difference_yields_same_id() -> None:
    field_id = _source_field_id()
    first = FieldValueEvidence.new(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
    )
    second = FieldValueEvidence.new(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW + timedelta(hours=1),
    )
    assert first.field_value_evidence_id == second.field_value_evidence_id


def test_evidence_reference_difference_yields_same_id() -> None:
    field_id = _source_field_id()
    first = FieldValueEvidence.new(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
        evidence_reference=None,
    )
    second = FieldValueEvidence.new(
        source_field_id=field_id,
        source_record_reference="100045",
        observed_representation="Acme Taiwan Ltd",
        observed_at=NOW,
        received_at=NOW,
        evidence_reference="batch-42",
    )
    assert first.field_value_evidence_id == second.field_value_evidence_id


def test_arbitrary_inconsistent_id_is_rejected() -> None:
    with pytest.raises(
        ValidationException,
        match="Field Value Evidence ID is inconsistent",
    ):
        FieldValueEvidence(
            field_value_evidence_id=Identifier(uuid4()),
            source_field_id=_source_field_id(),
            source_record_reference="100045",
            observed_representation="Acme Taiwan Ltd",
            observed_at=NOW,
            received_at=NOW,
        )
