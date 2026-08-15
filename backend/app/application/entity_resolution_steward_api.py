"""Application boundary for the Entity Resolution Steward workspace
(Increment 3A Gate C). Tenant identity always comes from the verified
TrustedPrincipal, never from a request body or query parameter. Every read
is scoped through EntityResolutionStore's tenant-checked queries; every
decision is dispatched through
EvidenceResolutionEngine.decide_steward_action() (the single place
confirm/reject/unresolved/block-conflict outcome semantics are decided) and
persisted through EntityResolutionStore.append_decision()'s locked,
based_on_record_id-checked write -- so a stale decision is rejected before
anything is appended.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.entity_resolution.schemas import (
    CaseDetailResponse,
    CaseListResponse,
    CaseSummaryResponse,
    DecisionRequest,
    DecisionResponse,
    EvidenceProfileResponse,
    PolicyListResponse,
    PolicySummaryResponse,
    PreviewResponse,
    PriorDecisionSummary,
    SourceRepresentationSummary,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.domain.identity_resolution.evidence import decide
from app.domain.identity_resolution.model import (
    EvidenceProfile,
    ResolutionOutcome,
    StewardDecisionAction,
)
from app.domain.identity_resolution.policy import ResolutionPolicyDefinition
from app.domain.identity_resolution.service import EvidenceResolutionEngine
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.resolution_policy import ResolutionPolicyModel
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.resolution_policy_store import ResolutionPolicyStore

QUEUE_OUTCOMES: tuple[str, ...] = (
    ResolutionOutcome.POSSIBLE.value,
    ResolutionOutcome.UNRESOLVED.value,
    ResolutionOutcome.BLOCKED_CONFLICT.value,
)


class CaseNotFoundError(Exception):
    """Raised when a case is not found, or not owned by the acting tenant."""


class PolicyNotFoundError(Exception):
    """Raised when a referenced policy is not found, or not owned by the
    acting tenant."""


class NoEvidenceProfileError(Exception):
    """Raised when a case has no persisted evidence profile (an automated,
    name-only record, not a Gate B/C steward case) to preview or decide
    against."""


class IncompleteSourceProvenanceError(Exception):
    """Raised when a case references a source object or source system that
    cannot be resolved for the acting tenant. This is a server-side data-
    integrity fault (referenced provenance should always exist, given the
    tenant-ownership check performed before a record is ever appended) --
    it must never be silently swallowed into a shorter-than-expected
    source_representations list."""


class EntityResolutionStewardApiService:
    def __init__(self, sessions: "sessionmaker[Session]") -> None:
        self._sessions = sessions

    # -- reads -------------------------------------------------------------

    def list_cases(
        self, principal: TrustedPrincipal, *, outcomes: tuple[str, ...] | None = None
    ) -> CaseListResponse:
        tenant_id = principal.tenant_id
        with self._sessions() as session:
            store = EntityResolutionStore(session)
            records = store.list_current_records(
                tenant_id,
                outcomes=outcomes if outcomes else QUEUE_OUTCOMES,
                require_evidence_profile=True,
            )
            entity_ids = {
                r.enterprise_entity_id for r in records if r.enterprise_entity_id is not None
            }
            entity_names = self._entity_names(session, tenant_id, entity_ids)
            items = [
                CaseSummaryResponse(
                    understanding_key=EntityResolutionStore.understanding_key(
                        tuple(UUID(v) for v in record.supporting_source_object_ids)
                    ),
                    record_id=record.record_id,
                    outcome=record.outcome,
                    business_confidence=record.business_confidence,
                    policy_version=record.policy_version,
                    produced_at=record.produced_at.isoformat(),
                    supporting_source_object_count=len(record.supporting_source_object_ids),
                    candidate_enterprise_entity_id=record.enterprise_entity_id,
                    candidate_enterprise_entity_name=(
                        entity_names.get(record.enterprise_entity_id)
                        if record.enterprise_entity_id is not None
                        else None
                    ),
                )
                for record in sorted(records, key=lambda r: r.produced_at, reverse=True)
            ]
        return CaseListResponse(items=items)

    def get_case(
        self, principal: TrustedPrincipal, understanding_key: str
    ) -> CaseDetailResponse | None:
        tenant_id = principal.tenant_id
        with self._sessions() as session:
            store = EntityResolutionStore(session)
            record = store.get_current_record(tenant_id, understanding_key)
            if record is None:
                return None
            history = store.get_history(tenant_id, understanding_key)
            source_ids = tuple(UUID(v) for v in record.supporting_source_object_ids)
            source_representations = self._source_representations(session, tenant_id, source_ids)
            entity_name = None
            if record.enterprise_entity_id is not None:
                entity_name = self._entity_names(
                    session, tenant_id, {record.enterprise_entity_id}
                ).get(record.enterprise_entity_id)
            policy_name = None
            if record.policy_id is not None:
                policy_row = session.get(ResolutionPolicyModel, record.policy_id)
                if policy_row is not None and policy_row.tenant_id == tenant_id:
                    policy_name = policy_row.policy_name
            evidence_profile_response = None
            if record.evidence_profile is not None:
                evidence_profile_response = EvidenceProfileResponse.model_validate(
                    record.evidence_profile
                )
            prior_decision_count = 0
            previous_decision = None
            if history is not None:
                prior_decision_count = len(history.historical_record_references)
                if history.historical_record_references:
                    previous_id = UUID(history.historical_record_references[-1])
                    previous_record = store.get_record_by_id(tenant_id, previous_id)
                    if previous_record is not None:
                        previous_decision = PriorDecisionSummary(
                            record_id=previous_record.record_id,
                            outcome=previous_record.outcome,
                            business_confidence=previous_record.business_confidence,
                            produced_at=previous_record.produced_at.isoformat(),
                            actor_id=previous_record.actor_id,
                            decision_rationale=previous_record.decision_rationale,
                        )
            return CaseDetailResponse(
                understanding_key=understanding_key,
                record_id=record.record_id,
                outcome=record.outcome,
                business_confidence=record.business_confidence,
                structured_reasons=list(record.structured_reasons),
                narrative_explanation=record.narrative_explanation,
                produced_at=record.produced_at.isoformat(),
                policy_id=record.policy_id,
                policy_name=policy_name,
                policy_version=record.policy_version,
                evidence_profile=evidence_profile_response,
                candidate_enterprise_entity_id=record.enterprise_entity_id,
                candidate_enterprise_entity_name=entity_name,
                source_representations=source_representations,
                actor_id=record.actor_id,
                decision_rationale=record.decision_rationale,
                prior_decision_count=prior_decision_count,
                previous_decision=previous_decision,
            )

    def list_policies(self, principal: TrustedPrincipal) -> PolicyListResponse:
        with self._sessions() as session:
            store = ResolutionPolicyStore(session)
            models = store.list_for_tenant(principal.tenant_id)
            items = [self._policy_summary(model) for model in models]
        return PolicyListResponse(items=items)

    def preview(
        self, principal: TrustedPrincipal, understanding_key: str, policy_id: UUID
    ) -> PreviewResponse:
        """Read-only: calls Gate B's deterministic decide() against the
        case's already-persisted evidence profile and a candidate policy,
        without appending or mutating anything."""
        tenant_id = principal.tenant_id
        with self._sessions() as session:
            store = EntityResolutionStore(session)
            record = store.get_current_record(tenant_id, understanding_key)
            if record is None:
                raise CaseNotFoundError(understanding_key)
            if record.evidence_profile is None:
                raise NoEvidenceProfileError(understanding_key)
            policy_row = session.get(ResolutionPolicyModel, policy_id)
            if policy_row is None or policy_row.tenant_id != tenant_id:
                raise PolicyNotFoundError(str(policy_id))
            definition = ResolutionPolicyDefinition.from_definition_dict(policy_row.definition)
            profile = EvidenceProfile.from_record(record.evidence_profile)
            decision = decide(profile, definition)
            return PreviewResponse(
                policy_id=policy_id,
                policy_name=policy_row.policy_name,
                policy_version=policy_row.policy_version,
                outcome=decision.outcome.value,
                business_confidence=decision.business_confidence.value,
                score=decision.score,
                would_change_outcome=decision.outcome.value != record.outcome,
                structured_reasons=list(decision.structured_reasons),
            )

    # -- decision ------------------------------------------------------------

    def decide_case(
        self,
        principal: TrustedPrincipal,
        understanding_key: str,
        request: DecisionRequest,
        *,
        now: datetime | None = None,
    ) -> DecisionResponse:
        tenant_id = principal.tenant_id
        try:
            action = StewardDecisionAction(request.action)
        except ValueError as error:
            raise ValidationException(
                f"Unknown steward decision action: {request.action!r}"
            ) from error
        produced_at = now if now is not None else datetime.now(UTC)

        with self._sessions() as session, session.begin():
            store = EntityResolutionStore(session)
            current = store.get_current_record(tenant_id, understanding_key)
            if current is None:
                raise CaseNotFoundError(understanding_key)
            if current.evidence_profile is None:
                raise NoEvidenceProfileError(understanding_key)
            policy_row = session.get(ResolutionPolicyModel, request.policy_id)
            if policy_row is None or policy_row.tenant_id != tenant_id:
                raise PolicyNotFoundError(str(request.policy_id))

            definition = ResolutionPolicyDefinition.from_definition_dict(policy_row.definition)
            profile = EvidenceProfile.from_record(current.evidence_profile)
            engine = EvidenceResolutionEngine(definition, policy_id=request.policy_id)
            new_record = engine.decide_steward_action(
                tenant_id=tenant_id,
                supporting_source_object_ids=tuple(
                    UUID(v) for v in current.supporting_source_object_ids
                ),
                evidence_profile=profile,
                current_enterprise_entity_id=current.enterprise_entity_id,
                action=action,
                actor_id=principal.principal_id,
                decision_rationale=request.rationale,
                produced_at=produced_at,
            )
            # append_decision re-acquires the lock and re-checks
            # based_on_record_id itself: this is the sole authority for the
            # concurrency guarantee, independent of the (unlocked) read above.
            store.append_decision(
                new_record,
                understanding_key=understanding_key,
                based_on_record_id=request.based_on_record_id,
            )

        return DecisionResponse(
            record_id=new_record.record_id,
            understanding_key=understanding_key,
            outcome=new_record.outcome.value,
            business_confidence=new_record.business_confidence.value,
            produced_at=new_record.produced_at.isoformat(),
            policy_id=new_record.policy_id,
            policy_version=new_record.policy_version,
            narrative_explanation=new_record.narrative_explanation,
            structured_reasons=list(new_record.structured_reasons),
        )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _policy_summary(model: ResolutionPolicyModel) -> PolicySummaryResponse:
        definition = ResolutionPolicyDefinition.from_definition_dict(model.definition)
        return PolicySummaryResponse(
            policy_id=model.policy_id,
            policy_name=model.policy_name,
            policy_version=model.policy_version,
            preset_kind=model.preset_kind,
            resolved_threshold=definition.resolved_threshold,
            possible_threshold=definition.possible_threshold,
            high_confidence_threshold=definition.high_confidence_threshold,
            medium_confidence_threshold=definition.medium_confidence_threshold,
            min_corroborating_attributes=definition.min_corroborating_attributes,
            country_conflict_severity=definition.country_conflict_severity,
            parent_subsidiary_conflict_severity=definition.parent_subsidiary_conflict_severity,
        )

    @staticmethod
    def _entity_names(session: Session, tenant_id: str, entity_ids: set[UUID]) -> dict[UUID, str]:
        if not entity_ids:
            return {}
        rows = session.scalars(
            select(EnterpriseEntity).where(
                EnterpriseEntity.enterprise_entity_id.in_(entity_ids),
                EnterpriseEntity.tenant_id == tenant_id,
            )
        ).all()
        return {row.enterprise_entity_id: row.enterprise_entity_name for row in rows}

    @staticmethod
    def _source_representations(
        session: Session, tenant_id: str, source_ids: tuple[UUID, ...]
    ) -> list[SourceRepresentationSummary]:
        """Resolves every supporting source object/system for display.
        Deterministically ordered to match source_ids (the record's own
        persisted order) -- never SQL result order. Fails explicitly
        (IncompleteSourceProvenanceError) rather than silently returning a
        shorter list if any referenced object or system cannot be found for
        this tenant: a case's evidence must never appear to have fewer
        sources than it actually does."""
        if not source_ids:
            return []
        objects_by_id = {
            obj.source_object_id: obj
            for obj in session.scalars(
                select(SourceObject).where(
                    SourceObject.source_object_id.in_(source_ids),
                    SourceObject.tenant_id == tenant_id,
                )
            ).all()
        }
        missing_objects = [sid for sid in source_ids if sid not in objects_by_id]
        if missing_objects:
            raise IncompleteSourceProvenanceError(
                f"Missing source object(s) for tenant {tenant_id!r}: "
                f"{sorted(str(v) for v in missing_objects)}"
            )
        system_ids = {obj.source_system_id for obj in objects_by_id.values()}
        systems_by_id = {
            row.source_system_id: row.source_system_name
            for row in session.scalars(
                select(SourceSystem).where(
                    SourceSystem.source_system_id.in_(system_ids),
                    SourceSystem.tenant_id == tenant_id,
                )
            ).all()
        }
        missing_systems = system_ids - set(systems_by_id)
        if missing_systems:
            raise IncompleteSourceProvenanceError(
                f"Missing source system(s) for tenant {tenant_id!r}: "
                f"{sorted(str(v) for v in missing_systems)}"
            )
        return [
            SourceRepresentationSummary(
                source_object_id=sid,
                source_object_name=objects_by_id[sid].source_object_name,
                source_system_id=objects_by_id[sid].source_system_id,
                source_system_name=systems_by_id[objects_by_id[sid].source_system_id],
            )
            for sid in source_ids
        ]
