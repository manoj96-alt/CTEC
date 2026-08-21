import pytest

from app.domain.ontology_copilot.intent import (
    ParsedContextExplanationIntent,
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
    assert isinstance(result, ParsedIntent)
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


# ---------------------------------------------------------------------------
# Gate P (CDD-025): Information-Element context explanation intent
# ---------------------------------------------------------------------------


def test_recognizes_the_gate_p_context_explanation_question() -> None:
    result = parse_question(
        "What is the evidence status of Supplier Legal Name in Semiconductor Supply Chain Blueprint?"
    )
    assert result == ParsedContextExplanationIntent(
        intent=SupportedIntent.INFORMATION_ELEMENT_CONTEXT_EXPLANATION,
        information_element_name="Supplier Legal Name",
        blueprint_name="Semiconductor Supply Chain Blueprint",
    )


@pytest.mark.parametrize(
    "question,expected_element,expected_blueprint",
    [
        (
            "what is the evidence status of Supplier Legal Name in Blueprint A",
            "Supplier Legal Name",
            "Blueprint A",
        ),
        (
            "WHAT IS THE EVIDENCE STATUS OF Supplier Legal Name IN Blueprint A???",
            "Supplier Legal Name",
            "Blueprint A",
        ),
        (
            "  What   is the  evidence status of   Supplier Legal Name in Blueprint A?  ",
            "Supplier Legal Name",
            "Blueprint A",
        ),
        (
            'What is the evidence status of "Supplier Legal Name" in Blueprint A?',
            "Supplier Legal Name",
            "Blueprint A",
        ),
    ],
)
def test_gate_p_harmless_case_and_punctuation_variations_normalize(
    question: str, expected_element: str, expected_blueprint: str
) -> None:
    result = parse_question(question)
    assert isinstance(result, ParsedContextExplanationIntent)
    assert result.intent == SupportedIntent.INFORMATION_ELEMENT_CONTEXT_EXPLANATION
    assert result.information_element_name == expected_element
    assert result.blueprint_name == expected_blueprint


def test_gate_p_question_never_matches_the_existing_supplier_intent() -> None:
    result = parse_question("What is the evidence status of Supplier Legal Name in Blueprint A?")
    assert isinstance(result, ParsedContextExplanationIntent)


def test_existing_supplier_question_never_matches_the_gate_p_intent() -> None:
    result = parse_question("Which products depend on TSMC?")
    assert isinstance(result, ParsedIntent)
    assert result.intent == SupportedIntent.PRODUCTS_DEPENDING_ON_SUPPLIER
