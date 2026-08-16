"""Application service orchestrating Ask CTEC (Gate D, Priority 6): a
deterministic, read-only, non-LLM natural-language ontology exploration
capability, authorized by the PAD-001 Product-Internal Deterministic
Capability Boundary Clarification
(architecture/released/v1.9/PAD-001-Product-Internal-Deterministic-Capability-Boundary-Clarification-v1.0_FROZEN.md).

Never invokes ERM/SRM/ASM/KRM/DRM/GRM. Never mutates the ontology, enterprise
identity, institutional relationships, or any governance/decision/assertion/
knowledge record -- this is a read-only capability even though its endpoint
is a POST (the question is a request payload, not a command).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.domain.ontology_copilot.answer import compose_products_depending_on_supplier_answer
from app.domain.ontology_copilot.intent import (
    SupportedIntent,
    UnsupportedQuestionError,
    parse_question,
)
from app.domain.ontology_copilot.traversal import find_paths_to_target_type
from app.infrastructure.persistence.institutional_relationship_store import (
    InstitutionalRelationshipStore,
)

# Deterministic, statically-declared mapping from a supported intent to the
# governed entity type its answer targets. Extending the supported question
# family means adding another explicit entry here, never inferring one.
_TARGET_ENTITY_TYPE_BY_INTENT: dict[SupportedIntent, str] = {
    SupportedIntent.PRODUCTS_DEPENDING_ON_SUPPLIER: "Product",
}


class AskStatus(StrEnum):
    ANSWERED = "answered"
    NO_MATCH = "no_match"
    AMBIGUOUS_MATCH = "ambiguous_match"
    UNSUPPORTED_QUESTION = "unsupported_question"


@dataclass(frozen=True, slots=True)
class ResolvedEntitySummary:
    entity_id: str
    entity_name: str
    entity_type_name: str


@dataclass(frozen=True, slots=True)
class EvidenceStepSummary:
    step: int
    entity_id: str
    entity_name: str
    entity_type_name: str
    relationship_name: str | None


@dataclass(frozen=True, slots=True)
class AskResult:
    status: AskStatus
    intent: SupportedIntent | None
    answer: str
    resolved_entity: ResolvedEntitySummary | None
    result_names: tuple[str, ...]
    evidence: tuple[tuple[EvidenceStepSummary, ...], ...]
    reason: str | None = None


class OntologyCopilotApiService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def ask(self, principal: TrustedPrincipal, question: str) -> AskResult:
        try:
            parsed = parse_question(question)
        except UnsupportedQuestionError:
            return AskResult(
                status=AskStatus.UNSUPPORTED_QUESTION,
                intent=None,
                answer="This question type is not supported yet.",
                resolved_entity=None,
                result_names=(),
                evidence=(),
                reason="UNRECOGNIZED_QUESTION",
            )

        with self._sessions() as session:
            store = InstitutionalRelationshipStore(session)
            matches = store.find_enterprise_entities_by_name(
                principal.tenant_id, parsed.entity_text
            )

            if len(matches) == 0:
                return AskResult(
                    status=AskStatus.NO_MATCH,
                    intent=parsed.intent,
                    answer=(
                        "CTEC does not currently have sufficient governed ontology "
                        f"evidence to answer this question -- no governed entity named "
                        f"{parsed.entity_text!r} was found."
                    ),
                    resolved_entity=None,
                    result_names=(),
                    evidence=(),
                    reason="NO_MATCHING_ENTITY",
                )
            if len(matches) > 1:
                return AskResult(
                    status=AskStatus.AMBIGUOUS_MATCH,
                    intent=parsed.intent,
                    answer=(
                        "CTEC found more than one governed entity named "
                        f"{parsed.entity_text!r} and cannot determine which one you mean."
                    ),
                    resolved_entity=None,
                    result_names=(),
                    evidence=(),
                    reason="AMBIGUOUS_ENTITY",
                )

            resolved = matches[0]
            entities_by_id, edges = store.load_tenant_graph(principal.tenant_id)
            target_type = _TARGET_ENTITY_TYPE_BY_INTENT[parsed.intent]
            paths = find_paths_to_target_type(
                start_entity=resolved,
                entities_by_id=entities_by_id,
                edges=edges,
                target_entity_type_name=target_type,
            )
            composed = compose_products_depending_on_supplier_answer(
                supplier_name=resolved.entity_name, paths=paths
            )

            return AskResult(
                status=AskStatus.ANSWERED,
                intent=parsed.intent,
                answer=composed.answer,
                resolved_entity=ResolvedEntitySummary(
                    entity_id=str(resolved.entity_id),
                    entity_name=resolved.entity_name,
                    entity_type_name=resolved.entity_type_name,
                ),
                result_names=composed.product_names,
                evidence=tuple(
                    tuple(
                        EvidenceStepSummary(
                            step=step.step,
                            entity_id=str(step.entity_id),
                            entity_name=step.entity_name,
                            entity_type_name=step.entity_type_name,
                            relationship_name=step.relationship_name,
                        )
                        for step in path.steps
                    )
                    for path in paths
                ),
            )
