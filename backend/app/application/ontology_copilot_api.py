"""Application service orchestrating Ask CTEC (Gate D, Priority 6): a
deterministic, read-only, non-LLM natural-language ontology exploration
capability, authorized by the PAD-001 Product-Internal Deterministic
Capability Boundary Clarification
(architecture/released/v1.9/PAD-001-Product-Internal-Deterministic-Capability-Boundary-Clarification-v1.0_FROZEN.md).

Never invokes ERM/SRM/ASM/KRM/DRM/GRM. Never mutates the ontology, enterprise
identity, institutional relationships, or any governance/decision/assertion/
knowledge record -- this is a read-only capability even though its endpoint
is a POST (the question is a request payload, not a command).

Also orchestrates Gate P (CDD-025; Context Explanation Artifact
Authorization): a second, independent deterministic intent that resolves a
Blueprint InformationElementRequirement and consumes the already-governed
Blueprint -> Gate I -> H4 -> Gate N chain (each invoked unmodified, exactly
once) to render a fixed-template explanation of the composed
(coverage_status, evidence_availability_status) pair. Gate N remains the
sole authority for that composition -- this service never reimplements it.
Gate J is not consumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityApplicationService,
)
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import SemanticMappingResolutionApplicationService
from app.domain.blueprint import Blueprint, InformationElementRequirement, Obligation
from app.domain.ontology_copilot.answer import (
    compose_information_element_context_explanation_answer,
    compose_products_depending_on_supplier_answer,
)
from app.domain.ontology_copilot.intent import (
    ParsedContextExplanationIntent,
    SupportedIntent,
    UnsupportedQuestionError,
    parse_question,
)
from app.domain.ontology_copilot.traversal import find_paths_to_target_type
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.institutional_relationship_store import (
    InstitutionalRelationshipStore,
)
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl

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


class GatePAskStatus(StrEnum):
    ANSWERED = "answered"
    UNSUPPORTED_QUESTION = "unsupported_question"
    BLUEPRINT_NOT_FOUND = "blueprint_not_found"
    INFORMATION_ELEMENT_NOT_FOUND = "information_element_not_found"
    INFORMATION_ELEMENT_AMBIGUOUS = "information_element_ambiguous"
    UPSTREAM_INTEGRITY_FAILURE = "upstream_integrity_failure"


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
class InformationElementContextExplanationResult:
    """Gate P (CDD-025 §11): the closed, typed result contract. Every
    identity/context field is `None` unless its own resolution step
    succeeded -- `coverage_status`/`evidence_availability_status` are `None`
    for every non-ANSWERED status (CDD-025 §19, binding)."""

    status: GatePAskStatus
    blueprint_id: UUID | None
    blueprint_version_number: int | None
    information_element_requirement_id: UUID | None
    information_element_name: str | None
    obligation: Obligation | None
    coverage_status: CoverageStatus | None
    evidence_availability_status: EvidenceAvailabilityStatus | None
    answer: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AskResult:
    status: AskStatus
    intent: SupportedIntent | None
    answer: str
    resolved_entity: ResolvedEntitySummary | None
    result_names: tuple[str, ...]
    evidence: tuple[tuple[EvidenceStepSummary, ...], ...]
    reason: str | None = None
    context_explanation: InformationElementContextExplanationResult | None = None


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

        if isinstance(parsed, ParsedContextExplanationIntent):
            return self._ask_information_element_context_explanation(principal, parsed)

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

    def _ask_information_element_context_explanation(
        self, principal: TrustedPrincipal, parsed: ParsedContextExplanationIntent
    ) -> AskResult:
        with self._sessions() as session:
            blueprint_service = BlueprintApplicationService(
                repository=BlueprintRepositoryImpl(session)
            )
            try:
                blueprint = blueprint_service.get_approved_by_name(parsed.blueprint_name)
            except ValidationException:
                # More than one Approved Blueprint sharing this name is a governed-data
                # integrity violation (BlueprintRepositoryImpl's own contract), never an
                # ordinary "not found" outcome -- must not collapse into BLUEPRINT_NOT_FOUND.
                return self._wrap_context_explanation(
                    AskStatus.NO_MATCH, self._upstream_integrity_failure()
                )
            if blueprint is None:
                return self._wrap_context_explanation(
                    AskStatus.NO_MATCH,
                    InformationElementContextExplanationResult(
                        status=GatePAskStatus.BLUEPRINT_NOT_FOUND,
                        blueprint_id=None,
                        blueprint_version_number=None,
                        information_element_requirement_id=None,
                        information_element_name=None,
                        obligation=None,
                        coverage_status=None,
                        evidence_availability_status=None,
                        answer=(
                            "CTEC does not currently have an Approved Blueprint named "
                            f"{parsed.blueprint_name!r}."
                        ),
                        reason="BLUEPRINT_NOT_FOUND",
                    ),
                )

            matches = [
                element
                for concept in blueprint.concept_requirements
                for element in concept.information_element_requirements
                if element.element_name.value == parsed.information_element_name
            ]
            if len(matches) == 0:
                return self._wrap_context_explanation(
                    AskStatus.NO_MATCH,
                    InformationElementContextExplanationResult(
                        status=GatePAskStatus.INFORMATION_ELEMENT_NOT_FOUND,
                        blueprint_id=blueprint.blueprint_id.value,
                        blueprint_version_number=blueprint.version_number,
                        information_element_requirement_id=None,
                        information_element_name=None,
                        obligation=None,
                        coverage_status=None,
                        evidence_availability_status=None,
                        answer=(
                            "CTEC could not find an Information Element named "
                            f"{parsed.information_element_name!r} in the "
                            f"{parsed.blueprint_name} Blueprint."
                        ),
                        reason="INFORMATION_ELEMENT_NOT_FOUND",
                    ),
                )
            if len(matches) > 1:
                return self._wrap_context_explanation(
                    AskStatus.AMBIGUOUS_MATCH,
                    InformationElementContextExplanationResult(
                        status=GatePAskStatus.INFORMATION_ELEMENT_AMBIGUOUS,
                        blueprint_id=blueprint.blueprint_id.value,
                        blueprint_version_number=blueprint.version_number,
                        information_element_requirement_id=None,
                        information_element_name=None,
                        obligation=None,
                        coverage_status=None,
                        evidence_availability_status=None,
                        answer=(
                            "CTEC found more than one Information Element named "
                            f"{parsed.information_element_name!r} in the "
                            f"{parsed.blueprint_name} Blueprint and cannot determine which one "
                            "you mean."
                        ),
                        reason="INFORMATION_ELEMENT_AMBIGUOUS",
                    ),
                )

            requirement = matches[0]

            try:
                coverage_result = SemanticCoverageEvaluationApplicationService(
                    blueprint_service=blueprint_service,
                    resolver=SemanticMappingResolutionApplicationService(
                        repository=SemanticMappingRepositoryImpl(session)
                    ),
                ).evaluate(blueprint_name=parsed.blueprint_name, tenant_id=principal.tenant_id)
                evidence_availability_results = (
                    InformationElementEvidenceAvailabilityApplicationService(
                        evidence_provider=FieldValueEvidenceRepositoryImpl(session)
                    ).evaluate(coverage_result=coverage_result)
                )
                composed = InformationElementContextAvailabilityApplicationService().compose(
                    coverage_result=coverage_result,
                    evidence_availability_results=evidence_availability_results,
                )
            except ValidationException:
                return self._wrap_context_explanation(
                    AskStatus.NO_MATCH,
                    self._upstream_integrity_failure(blueprint, requirement),
                )

            matched = next(
                (
                    c
                    for c in composed
                    if c.information_element_requirement_id
                    == requirement.information_element_requirement_id.value
                ),
                None,
            )
            if matched is None:
                # Structural invariant, not an expected runtime path: Gate I's own
                # coverage_result always includes every InformationElementRequirement of
                # the resolved Blueprint, and Gate N returns exactly one composed result
                # per element it is supplied -- reaching here would already have raised
                # ValidationException above. Handled identically for defense in depth,
                # never as a silently fabricated answer.
                return self._wrap_context_explanation(
                    AskStatus.NO_MATCH,
                    self._upstream_integrity_failure(blueprint, requirement),
                )

            answer_text = compose_information_element_context_explanation_answer(
                blueprint_name=parsed.blueprint_name,
                information_element_name=requirement.element_name.value,
                coverage_status=matched.coverage_status.value,
                evidence_availability_status=(
                    matched.evidence_availability_status.value
                    if matched.evidence_availability_status is not None
                    else None
                ),
            )
            return self._wrap_context_explanation(
                AskStatus.ANSWERED,
                InformationElementContextExplanationResult(
                    status=GatePAskStatus.ANSWERED,
                    blueprint_id=blueprint.blueprint_id.value,
                    blueprint_version_number=blueprint.version_number,
                    information_element_requirement_id=(
                        requirement.information_element_requirement_id.value
                    ),
                    information_element_name=requirement.element_name.value,
                    obligation=requirement.obligation,
                    coverage_status=matched.coverage_status,
                    evidence_availability_status=matched.evidence_availability_status,
                    answer=answer_text,
                    reason=None,
                ),
            )

    @staticmethod
    def _upstream_integrity_failure(
        blueprint: Blueprint | None = None,
        requirement: InformationElementRequirement | None = None,
    ) -> InformationElementContextExplanationResult:
        return InformationElementContextExplanationResult(
            status=GatePAskStatus.UPSTREAM_INTEGRITY_FAILURE,
            blueprint_id=blueprint.blueprint_id.value if blueprint is not None else None,
            blueprint_version_number=(blueprint.version_number if blueprint is not None else None),
            information_element_requirement_id=(
                requirement.information_element_requirement_id.value
                if requirement is not None
                else None
            ),
            information_element_name=(
                requirement.element_name.value if requirement is not None else None
            ),
            obligation=None,
            coverage_status=None,
            evidence_availability_status=None,
            answer=(
                "CTEC could not produce a governed context explanation for this requirement "
                "because the upstream governed evaluation chain reported an integrity violation."
            ),
            reason="UPSTREAM_INTEGRITY_FAILURE",
        )

    @staticmethod
    def _wrap_context_explanation(
        status: AskStatus, explanation: InformationElementContextExplanationResult
    ) -> AskResult:
        return AskResult(
            status=status,
            intent=SupportedIntent.INFORMATION_ELEMENT_CONTEXT_EXPLANATION,
            answer=explanation.answer,
            resolved_entity=None,
            result_names=(),
            evidence=(),
            reason=explanation.reason,
            context_explanation=explanation,
        )
