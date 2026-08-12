from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.ontology_activation import OntologyActivationService
from app.application.supplier_risk_api import SupplierRiskApiService
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.integration.contracts import AuthorityContext
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.persistence.contracts import (
    AttemptProjection,
    ExecutionSummaryProjection,
    ReplayAuthorization,
    ReplayOptionProjection,
    ResultProjection,
    RetryAuthorization,
    StageProjection,
)
from app.runtime.recovery import ValidatedRecoveryInvocation


class _StubStore:
    """Minimal ExecutionApiStore stub returning one canned result — isolates
    this test to the ontology-activation wiring, since result derivation
    itself is already covered by test_supplier_risk_pipeline.py and is
    entirely unmodified by this change."""

    def __init__(self, projection: ResultProjection) -> None:
        self._projection = projection

    def list_executions(
        self, tenant_id: str, *, offset: int, limit: int, state: str | None = None
    ) -> tuple[ExecutionSummaryProjection, ...]:
        return ()

    def list_attempts(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[AttemptProjection, ...]:
        return ()

    def list_stages(
        self, logical_execution_id: UUID, execution_id: UUID, tenant_id: str
    ) -> tuple[StageProjection, ...]:
        return ()

    def get_result_for_logical(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> ResultProjection | None:
        return self._projection

    def replay_options(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[ReplayOptionProjection, ...]:
        return ()

    def prepare_retry(
        self,
        original_execution_id: UUID,
        authorization: RetryAuthorization,
        authority_context: AuthorityContext,
    ) -> ValidatedRecoveryInvocation:
        raise AssertionError("not exercised by this test")

    def prepare_replay(
        self,
        original_execution_id: UUID,
        authorization: ReplayAuthorization,
        authority_context: AuthorityContext,
    ) -> ValidatedRecoveryInvocation:
        raise AssertionError("not exercised by this test")


def _principal() -> TrustedPrincipal:
    now = datetime.now(UTC)
    return TrustedPrincipal(
        principal_id="tester",
        tenant_id="tenant",
        scopes=(),
        roles=(),
        issuer="test",
        issued_at=now,
        expires_at=now,
    )


def _seeded_ontology_sessions() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
    return factory


def _result_projection() -> ResultProjection:
    return ResultProjection(
        execution_id=uuid4(),
        result_code="APPROVED",
        result_value="Qualify Nova Energy Systems as backup supplier.",
        actionable=True,
        completed_at=datetime.now(UTC),
        produced_record_references=(uuid4(),),
        terminal_classification="Completed",
        evidence_references=("EVID-0001",),
        provenance_references=("PROV-0001",),
    )


def test_result_populates_ontology_activation_fields_from_the_backend_resolution() -> None:
    sessions = _seeded_ontology_sessions()
    activation_service = OntologyActivationService(sessions)
    projection = _result_projection()
    service = SupplierRiskApiService(
        runtime=Mock(spec=CognitiveEngineRuntime),  # not exercised by result()
        store=_StubStore(projection),
        ontology_activation=activation_service,
    )

    response = service.result(uuid4(), _principal())

    assert response is not None
    assert response.ontology_id == "supplier-risk"
    assert response.ontology_version == "1.0"
    assert response.ontology_status == "Published"
    assert len(response.applicable_concept_ids) > 0
    assert len(response.applicable_relationship_ids) > 0
    assert response.ontology_quality_score == 1.0
    assert response.semantic_path == (
        "Supplier → supplies → Material → usedIn → BOM "
        "→ defines → Product → generatesRevenue → Revenue Exposure"
    )
    # the existing, unmodified fields are still populated exactly as before
    assert response.recommendation == projection.result_value
    assert response.governance_standing == projection.result_code
    assert response.actionable is True
    assert list(response.evidence_references) == ["EVID-0001"]


def test_result_leaves_ontology_fields_empty_when_activation_is_not_configured() -> None:
    projection = _result_projection()
    service = SupplierRiskApiService(
        runtime=Mock(spec=CognitiveEngineRuntime),
        store=_StubStore(projection),
        ontology_activation=None,
    )

    response = service.result(uuid4(), _principal())

    assert response is not None
    assert response.ontology_id is None
    assert response.ontology_version is None
    assert response.ontology_status is None
    assert response.applicable_concept_ids == []
    assert response.applicable_relationship_ids == []
    assert response.ontology_quality_score is None
    assert response.semantic_path is None
    # the recommendation itself is entirely unaffected by activation being absent
    assert response.recommendation == projection.result_value


def test_ontology_version_is_never_supplied_by_the_caller_only_resolved_server_side() -> None:
    """The activation contract's resolve() signature takes no arguments at
    all — there is no parameter through which a caller (including a
    browser-originated request) could supply or override the ontology
    version. This is a structural guarantee, not just a runtime check."""
    import inspect

    signature = inspect.signature(OntologyActivationService.resolve)
    assert list(signature.parameters) == ["self"]
