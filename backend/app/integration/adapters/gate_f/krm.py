"""Gate F KRM (CDD-015 §9-10, remediated per the merged Gate F Governed
Impact Decision Policy Clarification and Remediation Report, PR #69).
Derives governed knowledge for the four-condition policy from EXISTING
governed CTEC state -- never from caller-supplied request fields. Answers
WHAT DO WE KNOW -- never WHAT SHOULD WE DO (DRM's role, `gate_f/drm.py`)
or WHETHER HUMAN REVIEW IS REQUIRED (GRM's role, `gate_f/grm.py`).

Every governed fact is tri-state (True / False / Unknown): `None` means
"insufficient governed evidence," never a fabricated negative. Candidate
qualification/capacity/lead-time/cost are READ from assertions that must
already exist, subject-scoped to the Alternate Supplier entity (seeded by
a prior governed process, e.g. a demo/test seeding step -- CDD-015 §9's
"derives ... as assertions" is satisfied by KRM creating the `candidateFor`
relationship instance and ATTACHING the pre-existing assertions to it, not
by fabricating assertion content from caller input).

Deliberately separate from CDD-011's existing `integration/adapters/krm.py`
(CDD-015 §33), to avoid any regression risk to the existing, implemented
supplier-risk pipeline. Persists via the existing, unmodified physical
`assertions` / `institutional_relationships` / `institutional_relationship_assertions`
tables directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.institutional_relationship_assertion import (
    InstitutionalRelationshipAssertions,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType

CANDIDATE_FOR_RELATIONSHIP_TYPE_NAME = "candidateFor"
SUPPLIES_RELATIONSHIP_TYPE_NAME = "supplies"

SEVERITY_PREDICATE = "severity"
HIGH_SEVERITY_VALUE = "Severe"
REVENUE_PREDICATE = "annualRevenueUsd"
QUALIFICATION_PREDICATE = "qualification"
CAPACITY_PREDICATE = "capacity"
LEAD_TIME_PREDICATE = "leadTimeDays"
COST_PREDICATE = "costUsd"


@dataclass(frozen=True, slots=True)
class GovernedFact:
    """A tri-state governed fact: `value=None` means insufficient governed
    evidence (Unknown), never a fabricated negative. `assertion_id` is the
    evidence backing a known (`True`/`False`) value, if any exists."""

    value: bool | None
    assertion_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    alternate_supplier_entity_id: UUID
    material_entity_id: UUID
    institutional_relationship_id: UUID
    qualified: GovernedFact
    capacity_sufficient: GovernedFact
    lead_time_days: int | None
    cost_usd: float | None
    assertion_ids: tuple[UUID, ...]


class GateFKnowledgeAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def derive_high_severity_disruption(self, *, risk_event_entity_id: UUID | None) -> GovernedFact:
        """Condition 1. Reads the most current governed `severity` assertion
        on the Risk Event entity already reached via the existing
        `locatedIn`/`exposedTo` traversal chain (CDD-015 §4)."""
        if risk_event_entity_id is None:
            return GovernedFact(value=None)
        assertion = self._latest_assertion(risk_event_entity_id, SEVERITY_PREDICATE)
        if assertion is None:
            return GovernedFact(value=None)
        return GovernedFact(
            value=assertion.object_value == HIGH_SEVERITY_VALUE, assertion_id=assertion.assertion_id
        )

    def derive_single_source_exposure(
        self, *, tenant_id: str, material_entity_id: UUID, now: datetime
    ) -> GovernedFact:
        """Condition 2. Derived, not asserted: counts currently valid
        `supplies` relationships targeting the Material. Always resolvable
        -- Gate F only evaluates a Material already reached via a valid
        `supplies` edge, so at least one such relationship is guaranteed to
        exist."""
        relationship_type_id = self._relationship_type_id(SUPPLIES_RELATIONSHIP_TYPE_NAME)
        candidates = self._session.scalars(
            select(InstitutionalRelationship).where(
                InstitutionalRelationship.tenant_id == tenant_id,
                InstitutionalRelationship.relationship_type_id == relationship_type_id,
                InstitutionalRelationship.to_entity_id == material_entity_id,
                InstitutionalRelationship.lifecycle_state == "Active",
                InstitutionalRelationship.governance_status == "Approved",
                InstitutionalRelationship.effective_from <= now,
            )
        )
        currently_effective = [
            row for row in candidates if row.effective_to is None or row.effective_to > now
        ]
        return GovernedFact(value=len(currently_effective) == 1)

    def derive_revenue_materiality(
        self, *, revenue_exposure_entity_id: UUID | None, threshold_usd: float
    ) -> GovernedFact:
        """Condition 3. Reads the governed `annualRevenueUsd` assertion on
        the Revenue Exposure entity already reached via the existing
        single-hop `generatesRevenue` traversal (RFC-017 §1)."""
        if revenue_exposure_entity_id is None:
            return GovernedFact(value=None)
        assertion = self._latest_assertion(revenue_exposure_entity_id, REVENUE_PREDICATE)
        if assertion is None or assertion.object_value is None:
            return GovernedFact(value=None)
        try:
            amount = float(assertion.object_value)
        except ValueError:
            return GovernedFact(value=None)
        return GovernedFact(value=amount > threshold_usd, assertion_id=assertion.assertion_id)

    def derive_candidate_evidence(
        self,
        *,
        tenant_id: str,
        alternate_supplier_entity_id: UUID,
        material_entity_id: UUID,
        now: datetime,
    ) -> CandidateEvidence:
        """Condition 4. Creates the `candidateFor` relationship instance
        (CDD-015 §9 -- "Gate F MUST create one institutional_relationships
        row per (Alternate Supplier, Material) pair under evaluation") and
        attaches whatever governed qualification/capacity/lead-time/cost
        assertions already exist for the Alternate Supplier entity -- it
        never fabricates their content from caller input."""
        relationship_type_id = self._relationship_type_id(CANDIDATE_FOR_RELATIONSHIP_TYPE_NAME)
        relationship_id = uuid4()
        self._session.add(
            InstitutionalRelationship(
                institutional_relationship_id=relationship_id,
                tenant_id=tenant_id,
                institutional_relationship_name=f"gate-f-candidateFor:{relationship_id}",
                lifecycle_state="Active",
                effective_from=now,
                effective_to=None,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=now,
                modified_by=None,
                modified_on=None,
                version_number=1,
                previous_version_id=None,
                relationship_type_id=relationship_type_id,
                from_entity_id=alternate_supplier_entity_id,
                to_entity_id=material_entity_id,
                superseded_by_id=None,
            )
        )
        self._session.flush()

        qualification = self._latest_assertion(
            alternate_supplier_entity_id, QUALIFICATION_PREDICATE
        )
        capacity = self._latest_assertion(alternate_supplier_entity_id, CAPACITY_PREDICATE)
        lead_time = self._latest_assertion(alternate_supplier_entity_id, LEAD_TIME_PREDICATE)
        cost = self._latest_assertion(alternate_supplier_entity_id, COST_PREDICATE)

        assertion_ids: list[UUID] = []
        for found in (qualification, capacity, lead_time, cost):
            if found is None:
                continue
            self._session.add(
                InstitutionalRelationshipAssertions(
                    institutional_relationship_id=relationship_id,
                    assertion_id=found.assertion_id,
                )
            )
            assertion_ids.append(found.assertion_id)
        self._session.flush()

        return CandidateEvidence(
            alternate_supplier_entity_id=alternate_supplier_entity_id,
            material_entity_id=material_entity_id,
            institutional_relationship_id=relationship_id,
            qualified=GovernedFact(
                value=(qualification.object_value == "true") if qualification is not None else None,
                assertion_id=qualification.assertion_id if qualification is not None else None,
            ),
            capacity_sufficient=GovernedFact(
                value=(capacity.object_value == "true") if capacity is not None else None,
                assertion_id=capacity.assertion_id if capacity is not None else None,
            ),
            lead_time_days=(
                int(lead_time.object_value)
                if lead_time is not None and lead_time.object_value is not None
                else None
            ),
            cost_usd=(
                float(cost.object_value)
                if cost is not None and cost.object_value is not None
                else None
            ),
            assertion_ids=tuple(assertion_ids),
        )

    def _latest_assertion(self, subject_entity_id: UUID, predicate: str) -> Assertion | None:
        return self._session.scalars(
            select(Assertion)
            .where(
                Assertion.subject_entity_id == subject_entity_id,
                Assertion.predicate == predicate,
                Assertion.lifecycle_state == "Active",
                Assertion.governance_status == "Approved",
            )
            .order_by(Assertion.effective_from.desc(), Assertion.asserted_on.desc())
            .limit(1)
        ).first()

    def _relationship_type_id(self, name: str) -> UUID:
        relationship_type_id = self._session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == name
            )
        )
        if relationship_type_id is None:
            raise ValidationException(f"Relationship type {name!r} is not seeded")
        return relationship_type_id
