import json
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from app.domain.integration import SourceObject, SourceSystem
from app.domain.operational import EnterpriseEntity
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier

EAD_PATH = Path("../docs/persistence/traceability/EAD-001-v1.3.json")
IDENTIFIER = Identifier(UUID("20000000-0000-0000-0000-000000000001"))
TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)

ENTITY_TYPES = {
    "Enterprise Entity": EnterpriseEntity,
    "Source System": SourceSystem,
    "Source Object": SourceObject,
}


def _profile(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "lifecycle_state": LifecycleState.ACTIVE,
        "effective_from": TIMESTAMP,
        "effective_to": None,
        "governance_status": GovernanceStatus.APPROVED,
        "created_by": IDENTIFIER,
        "created_on": TIMESTAMP,
        "modified_by": None,
        "modified_on": None,
        "version_number": 1,
        "previous_version_id": None,
    }
    return values | overrides


def test_all_three_operational_entities_construct() -> None:
    entities = [
        EnterpriseEntity(
            enterprise_entity_id=IDENTIFIER,
            enterprise_entity_name=CanonicalName("Intel Corporation"),
            entity_type_id=IDENTIFIER,
            business_domain_id=IDENTIFIER,
            **_profile(),
        ),
        SourceSystem(
            source_system_id=IDENTIFIER,
            source_system_name=CanonicalName("SAP"),
            **_profile(),
        ),
        SourceObject(
            source_object_id=IDENTIFIER,
            source_object_name=CanonicalName("Supplier record 12345"),
            source_system_id=IDENTIFIER,
            **_profile(),
        ),
    ]
    assert len(entities) == 3


def test_operational_entity_attributes_match_ead_exactly() -> None:
    rows = json.loads(EAD_PATH.read_text())
    for ead_name, entity_type in ENTITY_TYPES.items():
        ead_attributes = {row["Attribute Name"] for row in rows if row["Entity"] == ead_name}
        domain_attributes = {field.name for field in fields(entity_type)}
        assert domain_attributes == ead_attributes


@pytest.mark.parametrize(
    ("entity_type", "identifier_field", "name_field", "extra_fields"),
    [
        (
            EnterpriseEntity,
            "enterprise_entity_id",
            "enterprise_entity_name",
            {"entity_type_id": IDENTIFIER, "business_domain_id": IDENTIFIER},
        ),
        (SourceSystem, "source_system_id", "source_system_name", {}),
        (
            SourceObject,
            "source_object_id",
            "source_object_name",
            {"source_system_id": IDENTIFIER},
        ),
    ],
)
def test_operational_entities_reject_invalid_identifiers(
    entity_type: type[EnterpriseEntity] | type[SourceSystem] | type[SourceObject],
    identifier_field: str,
    name_field: str,
    extra_fields: dict[str, Identifier],
) -> None:
    values = {
        identifier_field: "invalid",
        name_field: CanonicalName("Valid Name"),
        **extra_fields,
        **_profile(),
    }
    with pytest.raises(ValidationException, match="Identifier"):
        entity_type(**values)


def test_source_object_requires_source_system_reference() -> None:
    with pytest.raises(ValidationException, match="Source System"):
        SourceObject(
            source_object_id=IDENTIFIER,
            source_object_name=CanonicalName("Supplier record 12345"),
            source_system_id="invalid",  # type: ignore[arg-type]
            **_profile(),
        )


def test_enterprise_entity_requires_structural_classification_references() -> None:
    with pytest.raises(ValidationException, match="Entity Type"):
        EnterpriseEntity(
            enterprise_entity_id=IDENTIFIER,
            enterprise_entity_name=CanonicalName("Intel Corporation"),
            entity_type_id="invalid",  # type: ignore[arg-type]
            business_domain_id=IDENTIFIER,
            **_profile(),
        )


def test_operational_entities_reject_noncanonical_name_type() -> None:
    with pytest.raises(ValidationException, match="Canonical Name"):
        SourceSystem(
            source_system_id=IDENTIFIER,
            source_system_name="SAP",  # type: ignore[arg-type]
            **_profile(),
        )


def test_operational_entities_require_timezone_aware_datetimes() -> None:
    with pytest.raises(ValidationException, match="Effective From"):
        SourceSystem(
            source_system_id=IDENTIFIER,
            source_system_name=CanonicalName("SAP"),
            **_profile(effective_from=datetime(2026, 1, 1)),  # noqa: DTZ001
        )


def test_operational_entities_reject_noninteger_version() -> None:
    with pytest.raises(ValidationException, match="Version Number"):
        SourceObject(
            source_object_id=IDENTIFIER,
            source_object_name=CanonicalName("Supplier record 12345"),
            source_system_id=IDENTIFIER,
            **_profile(version_number=True),
        )
