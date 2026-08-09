from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from uuid import uuid4

from app.domain.assertion_engine import AssertionEngine, AssertionPolicy
from app.domain.decision_engine import (
    DecisionConfidenceClassificationService,
    DecisionEvaluationService,
)
from app.domain.governance_engine import (
    GovernanceConfidenceClassificationService,
    GovernanceEvaluationService,
)
from app.domain.identity_resolution import EntityResolutionEngine, ResolutionPolicy
from app.domain.knowledge_engine import KnowledgeEngine, KnowledgePolicy
from app.domain.semantic_resolution import SemanticResolutionEngine, SemanticResolutionPolicy
from app.integration.contracts import (
    AcceptanceEvidenceInput,
    AuthorityContext,
    IntegrationEnvelope,
    RiskSeverity,
    SourceObservation,
    SupplierEligibility,
    SupplierRiskRequest,
)
from app.integration.dependencies import IntegrationDependencies
from app.integration.pipeline import supplier_risk_capability_ports
from app.integration.supplier_risk_policy import SupplierRiskPolicy
from app.runtime.contracts import ExecutionSnapshot, InvocationRequest, InvocationStatus
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.execution_state import ExecutionState


class RecordingPersistence:
    def __init__(self) -> None:
        self.records: list[object] = []

    def entity_resolution(self, record: object) -> None:
        self.records.append(record)

    def semantic_resolution(self, record: object) -> None:
        self.records.append(record)

    def assertion(self, record: object) -> None:
        self.records.append(record)

    def knowledge(self, record: object) -> None:
        self.records.append(record)

    def decision(self, model: object, *, policy_satisfied: bool) -> None:
        self.records.append(model)

    def governance(self, model: object) -> None:
        self.records.append(model)


NOW = datetime(2026, 1, 1, tzinfo=UTC)


def build_request(
    *,
    conflicting: bool = False,
    governance_score: float = 0.95,
    conditions: tuple[str, ...] = (),
    verified: tuple[str, ...] = (),
) -> SupplierRiskRequest:
    supplier, concept = uuid4(), uuid4()
    observation = SourceObservation(
        uuid4(),
        uuid4(),
        "risk-1",
        "Supplier",
        supplier,
        "Supplier Risk",
        "active",
        RiskSeverity.HIGH,
        NOW,
        NOW,
        "evidence-1",
        conflicting=conflicting,
    )
    return SupplierRiskRequest(
        ("Supplier ABC",),
        (uuid4(),),
        ((supplier, "Supplier ABC"),),
        ("Supplier Risk",),
        ((concept, "Supplier Risk"),),
        uuid4(),
        uuid4(),
        uuid4(),
        NOW,
        (observation,),
        (
            SupplierEligibility(supplier, True, True, True, True, False),
            SupplierEligibility(uuid4(), True, True, True, True, True),
        ),
        1,
        1,
        1,
        1,
        0.95,
        governance_score,
        "erm-1",
        "srm-1",
        "asm-1",
        "knowledge-1",
        "decision-policy",
        "1",
        "supplier-risk-rule",
        "governance-policy",
        "1",
        AcceptanceEvidenceInput(
            uuid4(), "governance-authority", "acceptance-policy", "knowledge-1", NOW
        ),
        conditions,
        verified,
    )


def runtime_and_persistence() -> tuple[CognitiveEngineRuntime, RecordingPersistence]:
    persistence = RecordingPersistence()
    dependencies = IntegrationDependencies(
        EntityResolutionEngine(ResolutionPolicy("erm-1")),
        SemanticResolutionEngine(SemanticResolutionPolicy("srm-1")),
        AssertionEngine(AssertionPolicy("asm-1")),
        KnowledgeEngine(KnowledgePolicy("knowledge-1", frozenset({"governance-authority"}))),
        DecisionEvaluationService(),
        DecisionConfidenceClassificationService(high_threshold=0.9, medium_threshold=0.65),
        GovernanceEvaluationService(),
        GovernanceConfidenceClassificationService(high_threshold=0.9, medium_threshold=0.65),
        persistence,
        lambda: NOW,
    )
    return (
        CognitiveEngineRuntime(supplier_risk_capability_ports(dependencies, SupplierRiskPolicy())),
        persistence,
    )


def invoke(
    runtime: CognitiveEngineRuntime, request: SupplierRiskRequest
) -> tuple[InvocationRequest, ExecutionSnapshot]:
    request_id, correlation = uuid4(), uuid4()
    trusted_now = datetime.now(UTC)
    authority = AuthorityContext(
        "principal",
        "Service",
        "enterprise",
        ("risk-analyst",),
        ("supplier-risk:execute",),
        "AUTHORIZED",
        "authz",
        "gateway",
        request_id,
        correlation,
        trusted_now - timedelta(seconds=1),
        trusted_now + timedelta(days=1),
    )
    invocation = InvocationRequest(
        "2.0",
        correlation,
        request_id,
        uuid4(),
        "supplier-risk",
        IntegrationEnvelope(request).to_bytes(),
        authority,
        "1.0",
    )
    response = runtime.invoke(invocation)
    assert response.status is InvocationStatus.ACCEPTED and response.execution_identifier
    deadline = monotonic() + 2
    while monotonic() < deadline:
        snapshot = runtime.get_execution(response.execution_identifier)
        if snapshot and snapshot.state in {ExecutionState.COMPLETED, ExecutionState.FAILED}:
            return invocation, snapshot
        sleep(0.005)
    raise AssertionError("execution did not terminate")


def test_complete_six_capability_approved_path_and_replay() -> None:
    runtime, persistence = runtime_and_persistence()
    invocation, snapshot = invoke(runtime, build_request())
    assert snapshot.state is ExecutionState.COMPLETED
    assert snapshot.result_value == "APPROVED" and snapshot.actionable
    assert len(snapshot.produced_record_references) == 6 and len(persistence.records) == 6
    replay = runtime.invoke(invocation)
    assert replay.execution_identifier == snapshot.execution_identifier
    assert len(persistence.records) == 6


def test_missing_or_conflicting_evidence_is_successful_indeterminate_gate() -> None:
    runtime, persistence = runtime_and_persistence()
    _, snapshot = invoke(runtime, build_request(conflicting=True))
    assert snapshot.state is ExecutionState.COMPLETED
    assert snapshot.result_code == "EVIDENCE_INDETERMINATE"
    assert len(persistence.records) == 2


def test_rejected_and_conditional_paths_are_non_actionable_until_verified() -> None:
    runtime, _ = runtime_and_persistence()
    _, rejected = invoke(runtime, build_request(governance_score=0.2))
    assert rejected.result_value == "REJECTED" and not rejected.actionable
    runtime, _ = runtime_and_persistence()
    _, conditional = invoke(runtime, build_request(conditions=("human-check",)))
    assert conditional.result_value == "CONDITIONALLY_APPROVED" and not conditional.actionable
    runtime, _ = runtime_and_persistence()
    _, verified = invoke(
        runtime, build_request(conditions=("human-check",), verified=("human-check",))
    )
    assert verified.result_value == "CONDITIONALLY_APPROVED" and verified.actionable
