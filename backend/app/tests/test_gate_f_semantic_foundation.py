"""Gate F F-I1 semantic-foundation tests not already covered by
test_decision_engine.py (Decision Evaluation group persistence) or
test_ontology_seed.py (which already exercises REQUIRED_RELATIONSHIPS
dynamically, so the three RFC-017 relationship types are covered there
without modification).
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.decision_engine import DecisionEvaluationGroupModel
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.institutional_relationship_assertion import (
    InstitutionalRelationshipAssertions,
)
from app.infrastructure.persistence.ontology_seed import REQUIRED_RELATIONSHIPS

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_rfc_017_relationship_types_are_declared() -> None:
    assert ("assembledAt", "Product", "Facility") in REQUIRED_RELATIONSHIPS
    assert ("coveredBy", "Material", "Contract") in REQUIRED_RELATIONSHIPS
    assert ("candidateFor", "Alternate Supplier", "Material") in REQUIRED_RELATIONSHIPS


def test_institutional_relationship_assertions_support_multiple_contextual_assertions() -> None:
    """The existing generic institutional_relationship_assertions join table
    (composite primary key on (institutional_relationship_id, assertion_id),
    no additional uniqueness constraint) already permits associating
    arbitrarily many assertion_id rows with a single institutional_relationship_id
    -- e.g. multiple contextual assertions on one `candidateFor` relationship.
    No new persistence code is required for Gate F F-I1 to support this."""
    table = InstitutionalRelationshipAssertions.__table__
    assert {column.name for column in table.primary_key} == {
        "institutional_relationship_id",
        "assertion_id",
    }


def test_decision_evaluation_group_model_requires_tenant_id() -> None:
    with pytest.raises(ValidationException, match="tenant_id"):
        DecisionEvaluationGroupModel(decision_evaluation_id=uuid4(), tenant_id="  ", created_at=NOW)


def test_decision_evaluation_group_model_requires_timezone_aware_created_at() -> None:
    with pytest.raises(ValidationException, match="timezone-aware"):
        DecisionEvaluationGroupModel(
            decision_evaluation_id=uuid4(),
            tenant_id="tenant-a",
            created_at=NOW.replace(tzinfo=None),
        )
