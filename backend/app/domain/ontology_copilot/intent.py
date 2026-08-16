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


@dataclass(frozen=True, slots=True)
class ParsedIntent:
    intent: SupportedIntent
    entity_text: str


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


def parse_question(question: str) -> ParsedIntent:
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

    raise UnsupportedQuestionError(f"This question type is not supported yet: {question!r}")
