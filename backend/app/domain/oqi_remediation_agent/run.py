"""OQI5-I2 `AgentEvidencePacket` and `AgentRun` (CDD-043 §18-§19). The
packet is deterministically constructed by I2-owned application code from
existing persisted OQI1-4/I1 facts only -- never a live query the model
can wander through (CDD-043 §19). `AgentRun` is immutable and never keyed
by the packet digest: repeated invocation over an identical packet may
legitimately produce distinct `AgentRun` rows (CDD-043 §13/§18), because
the underlying model remains nondeterministic -- only packet construction,
validation, and aggregation are deterministic (CDD-043 §14/phase §14)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import UUID

from app.domain.oqi_remediation.case import FindingFamily
from app.domain.shared.exceptions import ValidationException

_SCHEMA_VERSION = "OQI5_AGENT_EVIDENCE_PACKET_V1"
_MAX_VALUE_LENGTH = 4000
_MAX_ROLE_LENGTH = 64


@dataclass(frozen=True, slots=True)
class PacketParticipant:
    """One N-source participant's observation, exactly as OQI1/2/3's own
    evidence already establishes it -- never re-derived or re-clustered by
    this packet (CDD-043 §17: OQI5 introduces zero new evaluation logic).
    `observed_value is None` means the participant's evidence was
    missing/empty for this evaluation, mirroring CDD-040's own EMPTY
    sentinel semantics."""

    role: str
    observed_value: str | None
    evidence_id: UUID | None
    is_conflicting: bool
    is_authoritative: bool

    def __post_init__(self) -> None:
        if not isinstance(self.role, str) or not (1 <= len(self.role) <= _MAX_ROLE_LENGTH):
            raise ValidationException("role must be non-blank bounded text")
        if self.observed_value is not None and not (
            isinstance(self.observed_value, str)
            and 1 <= len(self.observed_value) <= _MAX_VALUE_LENGTH
        ):
            raise ValidationException("observed_value must be None or non-blank bounded text")
        if self.evidence_id is not None and not isinstance(self.evidence_id, UUID):
            raise ValidationException("evidence_id must be None or a UUID")
        if not isinstance(self.is_conflicting, bool) or not isinstance(self.is_authoritative, bool):
            raise ValidationException("is_conflicting/is_authoritative must be explicit bools")


@dataclass(frozen=True, slots=True)
class PacketCandidate:
    """A deterministic I1 `RemediationCandidate`, projected read-only into
    packet form -- the model may reference `candidate_id`, it may never
    receive a channel through which to mutate `proposed_value` (CDD-043
    §21/§68)."""

    candidate_id: UUID
    target_source_object_id: UUID
    target_source_field_id: UUID
    proposed_value: str
    supporting_evidence_ids: tuple[UUID, ...]
    conflicting_evidence_ids: tuple[UUID, ...]
    basis: str

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, UUID):
            raise ValidationException("candidate_id must be a UUID")
        if not isinstance(self.target_source_object_id, UUID) or not isinstance(
            self.target_source_field_id, UUID
        ):
            raise ValidationException("target ids must be UUIDs")
        if not isinstance(self.proposed_value, str) or not (
            1 <= len(self.proposed_value) <= _MAX_VALUE_LENGTH
        ):
            raise ValidationException("proposed_value must be non-blank bounded text")
        if not isinstance(self.supporting_evidence_ids, tuple) or not all(
            isinstance(e, UUID) for e in self.supporting_evidence_ids
        ):
            raise ValidationException("supporting_evidence_ids must be a tuple of UUIDs")
        if not isinstance(self.conflicting_evidence_ids, tuple) or not all(
            isinstance(e, UUID) for e in self.conflicting_evidence_ids
        ):
            raise ValidationException("conflicting_evidence_ids must be a tuple of UUIDs")
        if not isinstance(self.basis, str) or not self.basis:
            raise ValidationException("basis must be non-blank text")


@dataclass(frozen=True, slots=True)
class PacketOntologyImpact:
    """A literal, read-only projection of one OQI4 `CurrentOntologyImpact`
    + its justifying `OntologyImpactEvaluation.outcome` -- `outcome` is
    carried through verbatim, including `IMPACT_UNKNOWN`, and this packet
    never upgrades it (CDD-043 §11/§18)."""

    impact_evaluation_id: UUID
    ontology_element_type: str
    ontology_element_id: UUID
    impact_kind: str
    outcome: str

    def __post_init__(self) -> None:
        if not isinstance(self.impact_evaluation_id, UUID):
            raise ValidationException("impact_evaluation_id must be a UUID")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        for label, value in (
            ("ontology_element_type", self.ontology_element_type),
            ("impact_kind", self.impact_kind),
            ("outcome", self.outcome),
        ):
            if not isinstance(value, str) or not value:
                raise ValidationException(f"{label} must be non-blank text")


@dataclass(frozen=True, slots=True)
class AgentEvidencePacket:
    """CDD-043 §19: the deterministic, bounded, single-tenant packet every
    governed `AgentRun` reasons over. Constructed once per remediation
    reasoning pass by I2-owned application code -- the model never issues
    its own query against this packet's source facts."""

    tenant_id: str
    finding_family: FindingFamily
    finding_id: UUID
    finding_state_revision: int
    case_id: UUID
    evaluation_id: UUID | None
    participants: tuple[PacketParticipant, ...]
    candidates: tuple[PacketCandidate, ...]
    ontology_impacts: tuple[PacketOntologyImpact, ...]
    role_version: int
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.finding_family, FindingFamily):
            raise ValidationException("finding_family must be a FindingFamily")
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if (
            not isinstance(self.finding_state_revision, int)
            or isinstance(self.finding_state_revision, bool)
            or self.finding_state_revision < 1
        ):
            raise ValidationException("finding_state_revision must be a positive integer")
        if not isinstance(self.case_id, UUID):
            raise ValidationException("case_id must be a UUID")
        if self.evaluation_id is not None and not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be None or a UUID")
        if not isinstance(self.participants, tuple) or not all(
            isinstance(p, PacketParticipant) for p in self.participants
        ):
            raise ValidationException("participants must be a tuple of PacketParticipant")
        if not isinstance(self.candidates, tuple) or not all(
            isinstance(c, PacketCandidate) for c in self.candidates
        ):
            raise ValidationException("candidates must be a tuple of PacketCandidate")
        if len({c.candidate_id for c in self.candidates}) != len(self.candidates):
            raise ValidationException("candidates must not contain duplicate candidate_id")
        if not isinstance(self.ontology_impacts, tuple) or not all(
            isinstance(i, PacketOntologyImpact) for i in self.ontology_impacts
        ):
            raise ValidationException("ontology_impacts must be a tuple of PacketOntologyImpact")
        if (
            not isinstance(self.role_version, int)
            or isinstance(self.role_version, bool)
            or self.role_version < 1
        ):
            raise ValidationException("role_version must be a positive integer")
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValidationException("schema_version must be non-blank text")

    def known_candidate_ids(self) -> frozenset[UUID]:
        return frozenset(c.candidate_id for c in self.candidates)

    def known_evidence_ids(self) -> frozenset[UUID]:
        """The complete closed universe of evidence ids the model may
        reference -- every participant's own evidence id, plus every
        candidate's supporting/conflicting evidence ids (CDD-043 §21)."""
        ids: set[UUID] = set()
        for p in self.participants:
            if p.evidence_id is not None:
                ids.add(p.evidence_id)
        for c in self.candidates:
            ids.update(c.supporting_evidence_ids)
            ids.update(c.conflicting_evidence_ids)
        return frozenset(ids)

    def known_impact_evaluation_ids(self) -> frozenset[UUID]:
        return frozenset(i.impact_evaluation_id for i in self.ontology_impacts)

    def candidate_by_id(self, candidate_id: UUID) -> PacketCandidate | None:
        for c in self.candidates:
            if c.candidate_id == candidate_id:
                return c
        return None

    def to_canonical_dict(self) -> dict[str, Any]:
        """The exact JSON-serializable payload sent to the model as task
        input (CDD-043 §22/§25/phase §16, §20) -- structurally separate
        from `system_instructions` (phase §23), and explicitly sorted so
        row/collection order never changes what the model is shown."""
        return {
            "tenant_id": self.tenant_id,
            "finding_family": self.finding_family.value,
            "finding_id": str(self.finding_id),
            "finding_state_revision": self.finding_state_revision,
            "participants": [
                {
                    "role": p.role,
                    "observed_value": p.observed_value,
                    "evidence_id": str(p.evidence_id) if p.evidence_id else None,
                    "is_conflicting": p.is_conflicting,
                    "is_authoritative": p.is_authoritative,
                }
                for p in sorted(self.participants, key=lambda p: p.role)
            ],
            "candidates": [
                {
                    "candidate_id": str(c.candidate_id),
                    "proposed_value": c.proposed_value,
                    "supporting_evidence_ids": sorted(str(e) for e in c.supporting_evidence_ids),
                    "conflicting_evidence_ids": sorted(str(e) for e in c.conflicting_evidence_ids),
                    "basis": c.basis,
                }
                for c in sorted(self.candidates, key=lambda c: str(c.candidate_id))
            ],
            "ontology_impacts": [
                {
                    "impact_evaluation_id": str(i.impact_evaluation_id),
                    "ontology_element_type": i.ontology_element_type,
                    "impact_kind": i.impact_kind,
                    "outcome": i.outcome,
                }
                for i in sorted(self.ontology_impacts, key=lambda i: str(i.impact_evaluation_id))
            ],
            "allowed_recommendation_types": [
                "RECOMMEND_CANDIDATE",
                "REQUEST_STEWARD_INVESTIGATION",
                "NO_REMEDIATION_RECOMMENDED",
            ],
            "schema_version": self.schema_version,
        }


def compute_evidence_packet_digest(packet: AgentEvidencePacket, *, role_version: int) -> str:
    """CDD-043 §18: a deterministic, order-independent canonical hash over
    `{finding_id, finding_state_revision, evaluation_id,
    sorted(candidate_ids), sorted(evidence_ids), impact_evaluation_id,
    role_version, schema_version}`. Governs provenance/idempotency
    analysis only -- it is never AgentRun identity (§13/phase §18: the
    same packet may legitimately produce distinct runs with distinct
    results)."""
    canonical = json.dumps(
        {
            "finding_id": str(packet.finding_id),
            "finding_state_revision": packet.finding_state_revision,
            "evaluation_id": str(packet.evaluation_id) if packet.evaluation_id else None,
            "candidate_ids": sorted(str(c) for c in packet.known_candidate_ids()),
            "evidence_ids": sorted(str(e) for e in packet.known_evidence_ids()),
            "impact_evaluation_ids": sorted(str(i) for i in packet.known_impact_evaluation_ids()),
            "role_version": role_version,
            "schema_version": packet.schema_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class AgentRunResultState(StrEnum):
    """CDD-043 §18: closed, exactly these three. No extra workflow states
    (phase §19). `FAILED` covers every provider-layer failure (timeout,
    auth, rate limit, network, malformed non-JSON response) --
    `REJECTED_OUTPUT` is reserved exclusively for well-formed JSON whose
    *content* the deterministic validator rejects."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED_OUTPUT = "REJECTED_OUTPUT"


_MAX_FAILURE_REASON_LENGTH = 200


@dataclass(frozen=True, slots=True)
class AgentRun:
    """CDD-043 §18: immutable. `run_id` is freshly generated per
    invocation -- never deduplicated by packet digest, since retries may
    legitimately differ (phase §13, §50). No chain-of-thought field exists
    in this schema (phase §15)."""

    run_id: UUID
    tenant_id: str
    case_id: UUID
    role_id: str
    role_version: int
    provider: str
    model: str
    evidence_packet_digest: str
    raw_output: str | None
    result_state: AgentRunResultState
    failure_reason: str | None
    created_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, UUID):
            raise ValidationException("run_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.case_id, UUID):
            raise ValidationException("case_id must be a UUID")
        if not isinstance(self.role_id, str) or not self.role_id:
            raise ValidationException("role_id must be non-blank text")
        if (
            not isinstance(self.role_version, int)
            or isinstance(self.role_version, bool)
            or self.role_version < 1
        ):
            raise ValidationException("role_version must be a positive integer")
        if not isinstance(self.provider, str) or not self.provider:
            raise ValidationException("provider must be non-blank text")
        if not isinstance(self.model, str) or not self.model:
            raise ValidationException("model must be non-blank text")
        if (
            not isinstance(self.evidence_packet_digest, str)
            or len(self.evidence_packet_digest) != 64
        ):
            raise ValidationException("evidence_packet_digest must be a 64-character hex digest")
        if not isinstance(self.result_state, AgentRunResultState):
            raise ValidationException("result_state must be an AgentRunResultState")
        if self.result_state is AgentRunResultState.FAILED:
            if self.raw_output is not None:
                raise ValidationException("a FAILED AgentRun must never store raw_output")
            if not self.failure_reason:
                raise ValidationException("a FAILED AgentRun must carry a failure_reason")
        else:
            if self.raw_output is None:
                raise ValidationException(
                    "SUCCEEDED/REJECTED_OUTPUT AgentRun must store its well-formed JSON raw_output"
                )
            try:
                json.loads(self.raw_output)
            except json.JSONDecodeError as exc:
                raise ValidationException(
                    "raw_output must be well-formed JSON when result_state is not FAILED"
                ) from exc
            if self.result_state is AgentRunResultState.REJECTED_OUTPUT and not self.failure_reason:
                raise ValidationException("a REJECTED_OUTPUT AgentRun must carry a failure_reason")
            if (
                self.result_state is AgentRunResultState.SUCCEEDED
                and self.failure_reason is not None
            ):
                raise ValidationException("a SUCCEEDED AgentRun must not carry a failure_reason")
        if self.failure_reason is not None and not (
            isinstance(self.failure_reason, str)
            and 1 <= len(self.failure_reason) <= _MAX_FAILURE_REASON_LENGTH
        ):
            raise ValidationException("failure_reason must be None or non-blank bounded text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


def evidence_ids_from_participants(participants: Sequence[PacketParticipant]) -> frozenset[UUID]:
    return frozenset(p.evidence_id for p in participants if p.evidence_id is not None)
