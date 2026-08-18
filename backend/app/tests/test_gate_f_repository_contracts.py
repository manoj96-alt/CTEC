"""Gate F public repository contract tests (merged Gate F Governed Impact
Decision Policy Clarification and Remediation Report, PR #69, Decisions
1-2). `GovernanceEvaluationRepositoryImpl.append()` accepts
`governed_record_type = "DecisionEvaluation"` only when the referenced
`decision_evaluations` group exists; every existing governed-record type
remains unaffected. `DecisionEvaluationRepositoryImpl.append_group_member`
is the public Gate F decision-persistence contract. No Gate F production
code may call either repository's `_to_orm` directly.
"""

import ast
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.domain.decision_engine import (
    DecisionConfidence,
    DecisionConfidenceLevel,
    DecisionEvaluationGroupModel,
    DecisionEvaluationGroupReference,
    DecisionEvaluationModel,
    DecisionEvaluationRecord,
    DecisionEvaluationService,
    DecisionExplanation,
    DecisionRecommendation,
    EvaluationOutcome,
    GoverningPolicyReference,
    PolicyVersion,
    SupportingKnowledgeReference,
)
from app.domain.governance_engine import (
    GovernanceConfidence,
    GovernanceConfidenceLevel,
    GovernanceEvaluationModel,
    GovernanceEvaluationService,
    GovernanceExplanation,
    GovernanceOutcome,
    GovernedRecordReference,
)
from app.domain.governance_engine import (
    GoverningPolicyReference as GovernanceGoverningPolicyReference,
)
from app.domain.governance_engine import PolicyVersion as GovernancePolicyVersion
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.decision_repository import (
    DecisionEvaluationRepositoryImpl,
    DecisionPersistenceModel,
)
from app.infrastructure.persistence.governance_repository import (
    GOVERNED_RECORD_MODELS,
    GovernanceEvaluationRepositoryImpl,
    GovernancePersistenceModel,
)
from app.infrastructure.persistence.models.governance_evaluation import GovernanceEvaluationORM

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _record(knowledge_id: UUID) -> DecisionEvaluationRecord:
    return DecisionEvaluationService().evaluate(
        knowledge_references=(SupportingKnowledgeReference(knowledge_id),),
        recommendation=DecisionRecommendation("Test recommendation"),
        outcome=EvaluationOutcome.REJECTED,
        confidence=DecisionConfidence(DecisionConfidenceLevel.HIGH),
        explanation=DecisionExplanation(("reason",), "narrative"),
        policy_reference=GoverningPolicyReference("test-policy"),
        policy_version=PolicyVersion("1.0"),
        policy_satisfied=False,
        effective_from=NOW,
        produced_timestamp=NOW,
    )


def test_governed_record_models_includes_decision_evaluation_unchanged_otherwise() -> None:
    assert GOVERNED_RECORD_MODELS.get("DecisionEvaluation") is not None
    assert set(GOVERNED_RECORD_MODELS) == {
        "Enterprise Entity Resolution",
        "Semantic Resolution",
        "Assertion",
        "Knowledge Evaluation",
        "Decision Evaluation",
        "DecisionEvaluation",
    }


def test_governance_append_accepts_decision_evaluation_when_group_exists(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"gate-f-repo-{uuid4()}"
    group_id = uuid4()
    with factory() as session:
        DecisionEvaluationRepositoryImpl(session).create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=group_id, tenant_id=tenant_id, created_at=NOW
            )
        )
        session.commit()

    with factory() as session:
        record = GovernanceEvaluationService().evaluate(
            governed_record_reference=GovernedRecordReference(group_id),
            governed_record_type="DecisionEvaluation",
            outcome=GovernanceOutcome.REQUIRES_REVIEW,
            confidence=GovernanceConfidence(GovernanceConfidenceLevel.HIGH),
            explanation=GovernanceExplanation(("reason",), "narrative"),
            policy_reference=GovernanceGoverningPolicyReference("test-policy"),
            policy_version=GovernancePolicyVersion("1.0"),
            exception_authorization_reference=None,
            policy_satisfied=False,
            human_review_required=True,
            effective_from=NOW,
            produced_timestamp=NOW,
        )
        GovernanceEvaluationRepositoryImpl(session).append(
            GovernancePersistenceModel(GovernanceEvaluationModel(record))
        )
        session.commit()

    with factory() as session:
        stored = session.get(GovernanceEvaluationORM, record.record_identifier)
        assert stored is not None
        assert stored.governed_record_type == "DecisionEvaluation"


def test_governance_append_rejects_nonexistent_decision_evaluation_reference(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        record = GovernanceEvaluationService().evaluate(
            governed_record_reference=GovernedRecordReference(uuid4()),
            governed_record_type="DecisionEvaluation",
            outcome=GovernanceOutcome.REQUIRES_REVIEW,
            confidence=GovernanceConfidence(GovernanceConfidenceLevel.HIGH),
            explanation=GovernanceExplanation(("reason",), "narrative"),
            policy_reference=GovernanceGoverningPolicyReference("test-policy"),
            policy_version=GovernancePolicyVersion("1.0"),
            exception_authorization_reference=None,
            policy_satisfied=False,
            human_review_required=True,
            effective_from=NOW,
            produced_timestamp=NOW,
        )
        with pytest.raises(ValidationException, match="does not exist"):
            GovernanceEvaluationRepositoryImpl(session).append(
                GovernancePersistenceModel(GovernanceEvaluationModel(record))
            )


def test_governance_append_still_rejects_unauthorized_record_type(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        record = GovernanceEvaluationService().evaluate(
            governed_record_reference=GovernedRecordReference(uuid4()),
            governed_record_type="Not A Real Type",
            outcome=GovernanceOutcome.REQUIRES_REVIEW,
            confidence=GovernanceConfidence(GovernanceConfidenceLevel.HIGH),
            explanation=GovernanceExplanation(("reason",), "narrative"),
            policy_reference=GovernanceGoverningPolicyReference("test-policy"),
            policy_version=GovernancePolicyVersion("1.0"),
            exception_authorization_reference=None,
            policy_satisfied=False,
            human_review_required=True,
            effective_from=NOW,
            produced_timestamp=NOW,
        )
        with pytest.raises(ValidationException, match="not authorized"):
            GovernanceEvaluationRepositoryImpl(session).append(
                GovernancePersistenceModel(GovernanceEvaluationModel(record))
            )


def test_decision_append_group_member_accepts_when_group_exists(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"gate-f-repo-{uuid4()}"
    group_id = uuid4()
    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        repository.create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=group_id, tenant_id=tenant_id, created_at=NOW
            )
        )
        session.commit()

    with factory() as session:
        model = DecisionEvaluationModel(
            record=_record(uuid4()),
            decision_evaluation_id=DecisionEvaluationGroupReference(group_id),
        )
        DecisionEvaluationRepositoryImpl(session).append_group_member(
            DecisionPersistenceModel(model, False)
        )
        session.commit()

    with factory() as session:
        records = DecisionEvaluationRepositoryImpl(session).records_for_group(
            group_id, tenant_id=tenant_id
        )
        assert len(records) == 1


def test_decision_append_group_member_rejects_nonexistent_group(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        model = DecisionEvaluationModel(
            record=_record(uuid4()),
            decision_evaluation_id=DecisionEvaluationGroupReference(uuid4()),
        )
        with pytest.raises(ValidationException, match="does not exist"):
            DecisionEvaluationRepositoryImpl(session).append_group_member(
                DecisionPersistenceModel(model, False)
            )


def test_decision_append_group_member_requires_decision_evaluation_id(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        model = DecisionEvaluationModel(record=_record(uuid4()))
        with pytest.raises(ValidationException, match="decision_evaluation_id"):
            DecisionEvaluationRepositoryImpl(session).append_group_member(
                DecisionPersistenceModel(model, False)
            )


def test_no_gate_f_production_code_calls_private_to_orm_directly() -> None:
    gate_f_root = Path(__file__).parents[1] / "integration" / "adapters" / "gate_f"
    application_files = [Path(__file__).parents[1] / "application" / "supply_chain_impact_api.py"]
    pipeline_files = [Path(__file__).parents[1] / "integration" / "gate_f_pipeline.py"]

    for path in list(gate_f_root.glob("*.py")) + application_files + pipeline_files:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "_to_orm":
                raise AssertionError(f"{path} calls a private _to_orm method directly")
