import ast
import json
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from app.domain.foundation import BusinessDomain, Country, Enterprise, EnterpriseType
from app.domain.semantic import EntityType, InstitutionalConcept, RelationshipType
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import (
    BusinessName,
    CanonicalName,
    Description,
    Identifier,
    ReferenceCode,
)

DOMAIN_ROOT = Path("app/domain")
EAD_PATH = Path("../docs/persistence/traceability/EAD-001-v1.3.json")
IDENTIFIER = Identifier(UUID("10000000-0000-0000-0000-000000000001"))
TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)

ENTITY_TYPES = {
    "Enterprise": Enterprise,
    "Enterprise Type": EnterpriseType,
    "Business Domain": BusinessDomain,
    "Country": Country,
    "Institutional Concept": InstitutionalConcept,
    "Entity Type": EntityType,
    "Relationship Type": RelationshipType,
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


def test_all_seven_authorized_entities_construct() -> None:
    entities = [
        Enterprise(
            enterprise_id=IDENTIFIER,
            enterprise_name=CanonicalName("CTEC"),
            legal_name=BusinessName("CTEC Incorporated"),
            enterprise_type_id=IDENTIFIER,
            country_id=IDENTIFIER,
            **_profile(),
        ),
        EnterpriseType(enterprise_type_id=IDENTIFIER, type_name=CanonicalName("Company")),
        BusinessDomain(
            business_domain_id=IDENTIFIER,
            enterprise_id=IDENTIFIER,
            domain_name=CanonicalName("Supply Chain"),
            **_profile(),
        ),
        Country(
            country_id=IDENTIFIER,
            country_name=CanonicalName("United States"),
            iso2_code=ReferenceCode("US"),
            iso3_code=ReferenceCode("USA"),
        ),
        InstitutionalConcept(
            institutional_concept_id=IDENTIFIER,
            institutional_concept_name=CanonicalName("Supplier"),
            enterprise_id=IDENTIFIER,
            **_profile(),
        ),
        EntityType(
            entity_type_id=IDENTIFIER,
            entity_type_name=CanonicalName("Organization"),
            institutional_concept_id=IDENTIFIER,
            **_profile(),
        ),
        RelationshipType(
            relationship_type_id=IDENTIFIER,
            relationship_type_name=CanonicalName("Supplied By"),
            **_profile(),
        ),
    ]
    assert len(entities) == 7


def test_domain_entity_attributes_match_ead_exactly() -> None:
    rows = json.loads(EAD_PATH.read_text())
    for ead_name, entity_type in ENTITY_TYPES.items():
        ead_attributes = {row["Attribute Name"] for row in rows if row["Entity"] == ead_name}
        domain_attributes = {field.name for field in fields(entity_type)}
        assert domain_attributes == ead_attributes


def test_authorized_value_objects_are_immutable_and_validate_text() -> None:
    assert CanonicalName("Enterprise").value == "Enterprise"
    assert BusinessName("Legal Name").value == "Legal Name"
    assert Description("Canonical description").value == "Canonical description"
    assert ReferenceCode("US").value == "US"
    with pytest.raises(ValidationException, match="non-empty"):
        CanonicalName(" ")
    with pytest.raises(ValidationException, match="UUID"):
        Identifier("not-a-uuid")  # type: ignore[arg-type]


def test_ead_enumerations_are_exact() -> None:
    assert {item.value for item in LifecycleState} == {
        "Draft",
        "Active",
        "Suspended",
        "Archived",
    }
    assert {item.value for item in GovernanceStatus} == {
        "Proposed",
        "Approved",
        "Retired",
        "Archived",
    }


@pytest.mark.parametrize(
    ("iso2", "iso3", "message"),
    [("USA", "USA", "ISO2"), ("US", "US", "ISO3")],
)
def test_country_rejects_invalid_reference_code_lengths(iso2: str, iso3: str, message: str) -> None:
    with pytest.raises(ValidationException, match=message):
        Country(
            country_id=IDENTIFIER,
            country_name=CanonicalName("United States"),
            iso2_code=ReferenceCode(iso2),
            iso3_code=ReferenceCode(iso3),
        )


def test_structural_entity_validation_rejects_invalid_types() -> None:
    with pytest.raises(ValidationException, match="Enterprise Type"):
        Enterprise(
            enterprise_id=IDENTIFIER,
            enterprise_name=CanonicalName("CTEC"),
            legal_name=None,
            enterprise_type_id="invalid",  # type: ignore[arg-type]
            country_id=IDENTIFIER,
            **_profile(),
        )
    with pytest.raises(ValidationException, match="Lifecycle State"):
        BusinessDomain(
            business_domain_id=IDENTIFIER,
            enterprise_id=IDENTIFIER,
            domain_name=CanonicalName("Supply Chain"),
            **_profile(lifecycle_state="Active"),
        )


def test_structural_entity_validation_requires_timezone() -> None:
    with pytest.raises(ValidationException, match="Effective From"):
        RelationshipType(
            relationship_type_id=IDENTIFIER,
            relationship_type_name=CanonicalName("Supplied By"),
            **_profile(effective_from=datetime(2026, 1, 1)),  # noqa: DTZ001
        )


def test_domain_has_no_forbidden_dependencies_or_artifact_classes() -> None:
    forbidden_imports = {
        "alembic",
        "fastapi",
        "sqlalchemy",
        "psycopg",
        "pydantic",
        "app.api",
        "app.application",
        "app.infrastructure",
    }
    declared_classes: set[str] = set()
    imported_modules: set[str] = set()
    canonical_domain_roots = (
        DOMAIN_ROOT / "foundation",
        DOMAIN_ROOT / "integration",
        DOMAIN_ROOT / "operational",
        DOMAIN_ROOT / "semantic",
        DOMAIN_ROOT / "shared",
    )
    for root in canonical_domain_roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text())
            declared_classes.update(
                node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            )
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_modules.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.add(node.module)

    assert not any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for module in imported_modules
        for forbidden in forbidden_imports
    )
    assert declared_classes == {
        "Enterprise",
        "EnterpriseType",
        "BusinessDomain",
        "Country",
        "InstitutionalConcept",
        "EntityType",
        "RelationshipType",
        "EnterpriseEntity",
        "SourceSystem",
        "SourceObject",
        "SourceField",
        "Identifier",
        "CanonicalName",
        "BusinessName",
        "Description",
        "ReferenceCode",
        "LifecycleState",
        "GovernanceStatus",
        "DomainException",
        "ValidationException",
    }
