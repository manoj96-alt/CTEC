"""Gate F GRM (CDD-015 §12, remediated per the merged Gate F Governed
Impact Decision Policy Clarification and Remediation Report, PR #69):
governance standing over the DRM recommendation. Owns the
`HUMAN_APPROVAL_REQUIRED` boundary -- not DRM's `HumanOverrideService`
(Product Owner Gate F F1 Decision 4).

Internal, persisted outcome remains the existing, unmodified
`GovernanceOutcome.REQUIRES_REVIEW` (no new enum value, no change to
`domain/governance_engine/model.py`). The Gate F-specific
`HUMAN_APPROVAL_REQUIRED` semantic is a presentation-layer projection
applied here, not a new governance state.

Persists via the existing, unmodified PUBLIC repository contract
`GovernanceEvaluationRepositoryImpl.append()`, now that
`governance_repository.py`'s `GOVERNED_RECORD_MODELS` accepts
`governed_record_type = "DecisionEvaluation"` (PR #69) -- never
`_to_orm` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.decision_engine.configuration import (
    GATE_F_POLICY_REFERENCE,
    GATE_F_POLICY_VERSION,
)
from app.domain.governance_engine import (
    GovernanceConfidence,
    GovernanceConfidenceLevel,
    GovernanceEvaluationModel,
    GovernanceExplanation,
    GovernanceOutcome,
    GovernedRecordReference,
    GoverningPolicyReference,
    PolicyVersion,
)
from app.domain.governance_engine.service import GovernanceEvaluationService
from app.infrastructure.persistence.governance_repository import (
    GovernanceEvaluationRepositoryImpl,
    GovernancePersistenceModel,
)

GATE_F_GOVERNED_RECORD_TYPE = "DecisionEvaluation"


class GateFGovernanceStanding(StrEnum):
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"


@dataclass(frozen=True, slots=True)
class GateFGovernanceResult:
    record_identifier: UUID
    standing: GateFGovernanceStanding


class GateFGovernanceAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def evaluate(self, *, decision_evaluation_id: UUID, now: datetime) -> GateFGovernanceResult:
        record = GovernanceEvaluationService().evaluate(
            governed_record_reference=GovernedRecordReference(decision_evaluation_id),
            governed_record_type=GATE_F_GOVERNED_RECORD_TYPE,
            outcome=GovernanceOutcome.REQUIRES_REVIEW,
            confidence=GovernanceConfidence(GovernanceConfidenceLevel.HIGH),
            explanation=GovernanceExplanation(
                (
                    (
                        "Gate F governed mitigation recommendation requires human approval "
                        "before any action is taken"
                    ),
                ),
                "Gate F stops at governance standing; no approval, rejection, or "
                "execution is implemented (CDD-015 §12, §14).",
            ),
            policy_reference=GoverningPolicyReference(GATE_F_POLICY_REFERENCE),
            policy_version=PolicyVersion(GATE_F_POLICY_VERSION),
            exception_authorization_reference=None,
            policy_satisfied=False,
            human_review_required=True,
            effective_from=now,
            produced_timestamp=now,
        )
        GovernanceEvaluationRepositoryImpl(self._session).append(
            GovernancePersistenceModel(GovernanceEvaluationModel(record))
        )
        return GateFGovernanceResult(
            record_identifier=record.record_identifier,
            standing=GateFGovernanceStanding.HUMAN_APPROVAL_REQUIRED,
        )
