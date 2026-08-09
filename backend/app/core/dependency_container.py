from base64 import urlsafe_b64decode
from dataclasses import dataclass

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import OidcJwtVerifier, TokenVerifier
from app.api.supplier_risk.rate_limit import RateLimiter
from app.application.supplier_risk_api import SupplierRiskApiService
from app.core.config import Settings, get_settings
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
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditRepository
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.session import create_session_factory
from app.integration.dependencies import IntegrationDependencies, SqlAlchemyCapabilityPersistence
from app.integration.pipeline import supplier_risk_capability_ports
from app.integration.supplier_risk_policy import SupplierRiskPolicy
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.persistence.crypto import AuthenticatedHandoffProtector
from app.runtime.persistence.repository import SqlAlchemyExecutionStore


@dataclass(frozen=True, slots=True)
class Container:
    """Composition root for dependencies implemented by the current layer."""

    settings: Settings
    token_verifier: TokenVerifier | None = None
    supplier_risk_api: SupplierRiskApiService | None = None
    security_audit: SecurityAuditService | None = None
    rate_limiter: RateLimiter | None = None


def build_container() -> Container:
    settings = get_settings()
    verifier = None
    if settings.oidc_issuer and settings.oidc_audience and settings.oidc_jwks_url:
        verifier = OidcJwtVerifier(settings)
    api_service = None
    audit = None
    if settings.database_url and settings.runtime_handoff_key:
        engine = create_database_engine(settings)
        sessions = create_session_factory(engine)
        persistence = SqlAlchemyCapabilityPersistence(sessions)
        dependencies = IntegrationDependencies(
            EntityResolutionEngine(
                ResolutionPolicy(
                    settings.resolution_policy_version,
                    settings.resolution_resolved_threshold,
                    settings.resolution_possible_threshold,
                    settings.resolution_high_confidence_threshold,
                    settings.resolution_medium_confidence_threshold,
                )
            ),
            SemanticResolutionEngine(
                SemanticResolutionPolicy(
                    settings.semantic_policy_version,
                    settings.semantic_resolved_threshold,
                    settings.semantic_possible_threshold,
                    settings.semantic_high_confidence_threshold,
                    settings.semantic_medium_confidence_threshold,
                )
            ),
            AssertionEngine(
                AssertionPolicy(
                    settings.assertion_policy_version,
                    settings.assertion_established_threshold,
                    settings.assertion_candidate_threshold,
                    settings.assertion_high_confidence_threshold,
                    settings.assertion_medium_confidence_threshold,
                )
            ),
            KnowledgeEngine(
                KnowledgePolicy(
                    settings.knowledge_policy_version,
                    frozenset(settings.knowledge_authorized_acceptance_authorities),
                    settings.knowledge_high_confidence_threshold,
                    settings.knowledge_medium_confidence_threshold,
                )
            ),
            DecisionEvaluationService(),
            DecisionConfidenceClassificationService(
                high_threshold=settings.decision_high_confidence_threshold,
                medium_threshold=settings.decision_medium_confidence_threshold,
            ),
            GovernanceEvaluationService(),
            GovernanceConfidenceClassificationService(
                high_threshold=settings.governance_high_confidence_threshold,
                medium_threshold=settings.governance_medium_confidence_threshold,
            ),
            persistence,
            __import__("functools").partial(
                __import__("datetime").datetime.now, __import__("datetime").UTC
            ),
        )
        try:
            handoff_key = urlsafe_b64decode(settings.runtime_handoff_key)
        except ValueError as exc:
            raise ValueError("Runtime handoff key must be URL-safe base64") from exc
        durable = SqlAlchemyExecutionStore(
            sessions,
            AuthenticatedHandoffProtector(
                {settings.runtime_handoff_key_id: handoff_key},
                settings.runtime_handoff_key_id,
            ),
        )
        runtime = CognitiveEngineRuntime(
            supplier_risk_capability_ports(dependencies, SupplierRiskPolicy()), durable
        )
        api_service = SupplierRiskApiService(runtime, durable)
        audit = SecurityAuditService(ApiSecurityAuditRepository(sessions))
    return Container(
        settings=settings,
        token_verifier=verifier,
        supplier_risk_api=api_service,
        security_audit=audit,
        rate_limiter=RateLimiter(settings.supplier_risk_rate_limit_per_minute),
    )
