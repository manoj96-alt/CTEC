"""Deterministic, non-LLM natural-language intent parser for the Ask CTEC
capability (Gate D, Priority 6). A fixed set of regex templates map a
question's surface text to a typed SupportedIntent, or the question is
explicitly UNSUPPORTED. No probabilistic interpretation, no external AI
call, no free-text reasoning -- exactly the boundary the PAD-001
Product-Internal Deterministic Capability Boundary Clarification
(architecture/released/v1.9/) requires.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class SupportedIntent(StrEnum):
    PRODUCTS_DEPENDING_ON_SUPPLIER = "products_depending_on_supplier"
    INFORMATION_ELEMENT_CONTEXT_EXPLANATION = "information_element_context_explanation"


@dataclass(frozen=True, slots=True)
class ParsedIntent:
    intent: SupportedIntent
    entity_text: str


@dataclass(frozen=True, slots=True)
class ParsedContextExplanationIntent:
    """Gate P (CDD-025 §10): a bounded question naming exactly one Blueprint
    and one Information Element. A distinct shape from `ParsedIntent`
    because this intent resolves two names, not one entity."""

    intent: SupportedIntent
    information_element_name: str
    blueprint_name: str


class UnsupportedQuestionError(Exception):
    """Raised when a question does not match any supported deterministic
    template. Never guessed around: the caller must present this as an
    explicit 'not supported yet' outcome, never a fabricated answer."""


# Deliberately narrow: "which products depend on <supplier>" with harmless
# case/whitespace/trailing-punctuation variation. Extending the supported
# question family means adding another explicit pattern here, never loosening
# this one to "understand" more.
_PRODUCTS_DEPENDING_ON_SUPPLIER = re.compile(
    r"^which\s+products?\s+depend(?:s)?\s+on\s+(?P<entity>.+?)\s*[?.!]*$",
    re.IGNORECASE,
)

# Gate P (CDD-025 §10): "what is the evidence status of <Information Element>
# in <Blueprint Name>" with harmless case/whitespace/trailing-punctuation
# variation. Deliberately narrow, exactly matching the existing intent's own
# discipline: extending the supported question family means adding another
# explicit pattern, never loosening this one to "understand" more.
_INFORMATION_ELEMENT_CONTEXT_EXPLANATION = re.compile(
    r"^what\s+is\s+the\s+evidence\s+status\s+of\s+(?P<element>.+?)\s+in\s+(?P<blueprint>.+?)\s*[?.!]*$",
    re.IGNORECASE,
)


def parse_question(question: str) -> ParsedIntent | ParsedContextExplanationIntent:
    normalized = " ".join(question.strip().split())
    if not normalized:
        raise UnsupportedQuestionError("Question is empty.")

    match = _PRODUCTS_DEPENDING_ON_SUPPLIER.match(normalized)
    if match:
        entity_text = match.group("entity").strip().strip("\"'").strip("?.! ").strip()
        if not entity_text:
            raise UnsupportedQuestionError("No supplier name was provided.")
        return ParsedIntent(
            intent=SupportedIntent.PRODUCTS_DEPENDING_ON_SUPPLIER,
            entity_text=entity_text,
        )

    match = _INFORMATION_ELEMENT_CONTEXT_EXPLANATION.match(normalized)
    if match:
        element_text = match.group("element").strip().strip("\"'").strip("?.! ").strip()
        blueprint_text = match.group("blueprint").strip().strip("\"'").strip("?.! ").strip()
        if not element_text or not blueprint_text:
            raise UnsupportedQuestionError(
                "Both an Information Element and a Blueprint name are required."
            )
        return ParsedContextExplanationIntent(
            intent=SupportedIntent.INFORMATION_ELEMENT_CONTEXT_EXPLANATION,
            information_element_name=element_text,
            blueprint_name=blueprint_text,
        )

    raise UnsupportedQuestionError(f"This question type is not supported yet: {question!r}")
