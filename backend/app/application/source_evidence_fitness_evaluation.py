"""Internal Gate T fitness-evaluation application service (CDD-031 §6-§14,
§17-§19; Gate T Artifact Authorization §6). For each already-produced H4
`InformationElementEvidenceAvailabilityResult`, classifies the resolved
`SourceField`'s persisted `FieldValueEvidence` set as `FIT`/`STALE`/
`CONFLICTING` using only exact-value comparison and freshness relative to a
caller-supplied `as_of`, or `None` when H4 classified the requirement
`NO_EVIDENCE`/`EVIDENCE_EMPTY`. Performs real I/O for evidence retrieval
only, via the narrow `EvidenceProvider` Protocol -- a deliberately
independent, locally-declared copy of H4's own identically-shaped Protocol,
never imported from H4's file (Gate T Artifact Authorization §5). Never
evaluates validity, format, accuracy, completeness beyond H4, or
referential integrity -- exclusively freshness and exact-value conflict."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityResult,
)
from app.domain.integration.field_value_evidence import FieldValueEvidence

_STALENESS_THRESHOLD = timedelta(days=7)


class EvidenceProvider(Protocol):
    """Structural contract satisfied by `FieldValueEvidenceRepositoryImpl`
    (unmodified) -- the sole evidence-retrieval path this service depends
    on. Declared independently of H4's own identically-shaped
    `EvidenceProvider` Protocol: a deliberate zero-coupling choice (Gate T
    Artifact Authorization §5), not a deduplication oversight."""

    def get_by_source_field(
        self, *, tenant_id: str, source_field_id: UUID
    ) -> tuple[FieldValueEvidence, ...]: ...


class EvidenceFitnessStatus(StrEnum):
    FIT = "FIT"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"


@dataclass(frozen=True, slots=True)
class InformationElementEvidenceFitnessResult:
    information_element_requirement_id: UUID
    source_field_id: UUID
    fitness_status: EvidenceFitnessStatus | None


class SourceEvidenceFitnessEvaluationApplicationService:
    def __init__(self, *, evidence_provider: EvidenceProvider) -> None:
        self.evidence_provider = evidence_provider

    def evaluate(
        self,
        *,
        evidence_availability_results: tuple[InformationElementEvidenceAvailabilityResult, ...],
        tenant_id: str,
        as_of: datetime,
    ) -> tuple[InformationElementEvidenceFitnessResult, ...]:
        results = [
            self._evaluate_one(h4_result, tenant_id, as_of)
            for h4_result in evidence_availability_results
        ]
        return self._sorted(results)

    def _evaluate_one(
        self,
        h4_result: InformationElementEvidenceAvailabilityResult,
        tenant_id: str,
        as_of: datetime,
    ) -> InformationElementEvidenceFitnessResult:
        if (
            h4_result.evidence_availability_status
            is not EvidenceAvailabilityStatus.EVIDENCE_PRESENT
        ):
            fitness_status = None
        else:
            evidence_rows = self.evidence_provider.get_by_source_field(
                tenant_id=tenant_id, source_field_id=h4_result.source_field_id
            )
            fitness_status = self._classify(evidence_rows, as_of)

        return InformationElementEvidenceFitnessResult(
            information_element_requirement_id=h4_result.information_element_requirement_id,
            source_field_id=h4_result.source_field_id,
            fitness_status=fitness_status,
        )

    @staticmethod
    def _classify(
        evidence_rows: tuple[FieldValueEvidence, ...], as_of: datetime
    ) -> EvidenceFitnessStatus:
        groups: dict[str, list[FieldValueEvidence]] = {}
        for row in evidence_rows:
            if row.observed_representation == "":
                continue
            groups.setdefault(row.source_record_reference, []).append(row)

        any_stale = False
        for rows in groups.values():
            distinct_values = {row.observed_representation for row in rows}
            if len(distinct_values) > 1:
                return EvidenceFitnessStatus.CONFLICTING
            most_recent_observed_at = max(row.observed_at for row in rows)
            if (
                most_recent_observed_at > as_of
                or (as_of - most_recent_observed_at) > _STALENESS_THRESHOLD
            ):
                any_stale = True

        return EvidenceFitnessStatus.STALE if any_stale else EvidenceFitnessStatus.FIT

    @staticmethod
    def _sorted(
        results: list[InformationElementEvidenceFitnessResult],
    ) -> tuple[InformationElementEvidenceFitnessResult, ...]:
        return tuple(sorted(results, key=lambda result: result.information_element_requirement_id))
