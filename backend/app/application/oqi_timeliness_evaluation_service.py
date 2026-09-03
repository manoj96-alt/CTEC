"""OQI-H5 Governed Timeliness evaluation orchestration (CDD-051 §3-§6, §12,
§13, §33). Mirrors `OqiIntegrityStructuralEvaluationService`'s exact
ordering discipline: resolve the governed policy (`NOT_EVALUABLE`, zero
row, if none exists -- CDD-051 §6 case 1) -> resolve the Approved
`SemanticMapping` for the policy's `InformationElementRequirement`
(`NOT_EVALUABLE` if none -- no source field is mapped, so there is nothing
to date, CDD-051 §33) -> resolve the single latest qualifying
`FieldValueEvidence` for that `SourceField`, filtered `received_at <=
evaluation_horizon` (`NOT_EVALUABLE` if none exists -- CDD-051 §6 case 3) ->
acquire the transaction-scoped advisory authority -> compute age against
`evaluation_horizon` (never wall-clock `now()`, CDD-051 §5, §13) for each
reason path whose threshold is governed (CDD-051 §6 case 2 skips a reason
path whose threshold is `NULL`) -> apply the frozen inclusive threshold
boundary (CDD-051 §4) -> persist the immutable ledger row idempotently ->
mutate the Finding only when the ledger insert was genuinely new.

`STALE_SOURCE_EVIDENCE` and `INGESTION_LATENCY_EXCEEDED` are evaluated
entirely independently -- a policy may govern one, the other, or both, and
their outcomes never influence one another (CDD-051 §4)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi_timeliness.evaluation import (
    TimelinessEvaluation,
    TimelinessFinding,
    TimelinessFindingType,
    apply_timeliness_finding_transition,
    derive_timeliness_evaluation_id,
    derive_timeliness_finding_id,
    timeliness_finding_identity_material,
)
from app.domain.oqi_timeliness.policy import TimelinessPolicy


class TimelinessEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> TimelinessFinding | None: ...

    def insert_evaluation_idempotent(
        self,
        *,
        evaluation_id: UUID,
        tenant_id: str,
        policy_id: UUID,
        policy_version: int,
        finding_type: str,
        source_object_id: UUID,
        field_value_evidence_id: UUID,
        outcome: str,
        evaluation_horizon: datetime,
        evaluated_on: datetime,
    ) -> bool: ...

    def upsert_finding(self, finding: TimelinessFinding, *, policy_version: int) -> None: ...


class QualifyingEvidenceLookup(Protocol):
    def select_latest_qualifying_evidence(
        self, *, tenant_id: str, source_field_id: UUID, evaluation_horizon: datetime
    ) -> object | None:  # returns a QualifyingEvidence-shaped object
        ...


class PolicyLookup(Protocol):
    def get_active_policy_for_anchor(
        self,
        *,
        tenant_id: str,
        information_element_requirement_id: UUID,
        business_process_id: UUID,
        business_process_version: int,
    ) -> TimelinessPolicy | None: ...


class SemanticMappingLookup(Protocol):
    def get_approved_by_information_element_requirement(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> object | None:  # returns a SemanticMappingResolution-shaped object
        ...


class OqiTimelinessEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: TimelinessEvaluationRepository,
        evidence_lookup: QualifyingEvidenceLookup,
        policy_lookup: PolicyLookup,
        semantic_mapping_lookup: SemanticMappingLookup,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._evidence_lookup = evidence_lookup
        self._policy_lookup = policy_lookup
        self._semantic_mapping_lookup = semantic_mapping_lookup
        self._clock = clock

    def evaluate_current_state(
        self,
        *,
        tenant_id: str,
        information_element_requirement_id: UUID,
        business_process_id: UUID,
        business_process_version: int,
        evaluation_horizon: datetime | None = None,
    ) -> tuple[TimelinessEvaluation, ...]:
        horizon = self._clock() if evaluation_horizon is None else evaluation_horizon
        if horizon.tzinfo is None:
            raise ValueError("evaluation_horizon must include a timezone")

        policy = self._policy_lookup.get_active_policy_for_anchor(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            business_process_id=business_process_id,
            business_process_version=business_process_version,
        )
        if policy is None:
            # CDD-051 §6 case 1: no ACTIVE TimelinessPolicy for this exact
            # anchor -- NOT_EVALUABLE, zero row, never a fabricated default
            # threshold.
            return ()

        mapping = self._semantic_mapping_lookup.get_approved_by_information_element_requirement(
            information_element_requirement_id, tenant_id
        )
        if mapping is None:
            # No SourceField is currently mapped to this InformationElement
            # -- there is no evidence to date (CDD-051 §33, §7's "practical
            # consequence" note). NOT_EVALUABLE, zero row.
            return ()

        evidence = self._evidence_lookup.select_latest_qualifying_evidence(
            tenant_id=tenant_id,
            source_field_id=mapping.source_field_id,  # type: ignore[attr-defined]
            evaluation_horizon=horizon,
        )
        if evidence is None:
            # CDD-051 §6 case 3: no qualifying FieldValueEvidence exists at
            # or before this evaluation_horizon -- NOT_EVALUABLE, zero row.
            return ()

        results: list[TimelinessEvaluation] = []
        for finding_type, threshold_seconds in (
            (TimelinessFindingType.STALE_SOURCE_EVIDENCE, policy.freshness_window_seconds),
            (TimelinessFindingType.INGESTION_LATENCY_EXCEEDED, policy.ingestion_sla_seconds),
        ):
            if threshold_seconds is None:
                # CDD-051 §6 case 2: this reason path's threshold is NULL
                # on the ACTIVE policy -- NOT_EVALUABLE for this type only,
                # the other reason path is unaffected.
                continue
            results.append(
                self._evaluate_one_reason_path(
                    tenant_id=tenant_id,
                    policy=policy,
                    finding_type=finding_type,
                    threshold_seconds=threshold_seconds,
                    source_object_id=evidence.source_object_id,  # type: ignore[attr-defined]
                    field_value_evidence_id=evidence.field_value_evidence_id,  # type: ignore[attr-defined]
                    observed_at=evidence.observed_at,  # type: ignore[attr-defined]
                    received_at=evidence.received_at,  # type: ignore[attr-defined]
                    evaluation_horizon=horizon,
                )
            )
        return tuple(results)

    def _evaluate_one_reason_path(
        self,
        *,
        tenant_id: str,
        policy: TimelinessPolicy,
        finding_type: TimelinessFindingType,
        threshold_seconds: int,
        source_object_id: UUID,
        field_value_evidence_id: UUID,
        observed_at: datetime,
        received_at: datetime,
        evaluation_horizon: datetime,
    ) -> TimelinessEvaluation:
        # CDD-051 §5: age is always computed against evaluation_horizon,
        # never wall-clock datetime.now() -- historical/as-of evaluation
        # remains reproducible regardless of when this code actually runs.
        if finding_type is TimelinessFindingType.STALE_SOURCE_EVIDENCE:
            age_seconds = int((evaluation_horizon - observed_at).total_seconds())
        else:
            age_seconds = int((received_at - observed_at).total_seconds())

        # CDD-051 §4: exact inclusive threshold boundary -- age_seconds ==
        # threshold_seconds is SATISFIED.
        outcome = (
            EvaluationOutcome.SATISFIED
            if age_seconds <= threshold_seconds
            else EvaluationOutcome.VIOLATED
        )

        identity_material = timeliness_finding_identity_material(
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            finding_type=finding_type,
            source_object_id=source_object_id,
        )
        # CDD-039 §24-§25 precedent: authority MUST be acquired before
        # persisting evaluation/Finding state.
        self._evaluation_repository.acquire_evaluation_authority(identity_material)

        finding_id = derive_timeliness_finding_id(
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            finding_type=finding_type,
            source_object_id=source_object_id,
        )
        existing_finding = self._evaluation_repository.get_finding(finding_id)
        next_finding = apply_timeliness_finding_transition(
            existing=existing_finding,
            outcome=outcome,
            finding_type=finding_type,
            evaluation_horizon=evaluation_horizon,
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            source_object_id=source_object_id,
        )

        evaluated_on = self._clock()
        evaluation_id = derive_timeliness_evaluation_id(
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            finding_type=finding_type,
            source_object_id=source_object_id,
            field_value_evidence_id=field_value_evidence_id,
            evaluation_horizon=evaluation_horizon,
        )
        evaluation = TimelinessEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            finding_type=finding_type,
            source_object_id=source_object_id,
            field_value_evidence_id=field_value_evidence_id,
            outcome=outcome,
            evaluation_horizon=evaluation_horizon,
            evaluated_on=evaluated_on,
        )

        # CDD-039 §20 precedent: idempotent replay -- a byte-identical
        # logical replay is a no-op, never a duplicate row and never a
        # second Finding mutation.
        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(
            evaluation_id=evaluation.evaluation_id,
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            finding_type=finding_type.value,
            source_object_id=source_object_id,
            field_value_evidence_id=field_value_evidence_id,
            outcome=outcome.value,
            evaluation_horizon=evaluation_horizon,
            evaluated_on=evaluated_on,
        )
        if newly_inserted and next_finding is not None:
            self._evaluation_repository.upsert_finding(next_finding, policy_version=policy.version)
        return evaluation
