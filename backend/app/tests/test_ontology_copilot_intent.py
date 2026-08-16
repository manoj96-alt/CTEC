import pytest

from app.domain.ontology_copilot.intent import (
    ParsedIntent,
    SupportedIntent,
    UnsupportedQuestionError,
    parse_question,
)


def test_recognizes_the_primary_demo_question() -> None:
    result = parse_question("Which products depend on TSMC?")
    assert result == ParsedIntent(
        intent=SupportedIntent.PRODUCTS_DEPENDING_ON_SUPPLIER, entity_text="TSMC"
    )


@pytest.mark.parametrize(
    "question,expected_entity",
    [
        ("which products depend on TSMC", "TSMC"),
        ("WHICH PRODUCTS DEPEND ON TSMC???", "TSMC"),
        ("  Which   products depend on   TSMC?  ", "TSMC"),
        ("Which product depends on TSMC.", "TSMC"),
        ("which products depend on Supplier A?", "Supplier A"),
        ('Which products depend on "TSMC"?', "TSMC"),
    ],
)
def test_harmless_case_and_punctuation_variations_normalize(
    question: str, expected_entity: str
) -> None:
    result = parse_question(question)
    assert result.intent == SupportedIntent.PRODUCTS_DEPENDING_ON_SUPPLIER
    assert result.entity_text == expected_entity


@pytest.mark.parametrize(
    "question",
    [
        "What is the weather today?",
        "Tell me about TSMC.",
        "Which suppliers are connected to Material A?",
        "",
        "   ",
        "Which products depend on ?",
    ],
)
def test_unsupported_question_fails_explicitly(question: str) -> None:
    with pytest.raises(UnsupportedQuestionError):
        parse_question(question)


def test_unsupported_question_never_silently_guesses_a_different_intent() -> None:
    # A question that is superficially close to the supported template but
    # is not it must not be coerced into the supported intent.
    with pytest.raises(UnsupportedQuestionError):
        parse_question("Which suppliers depend on TSMC?")
