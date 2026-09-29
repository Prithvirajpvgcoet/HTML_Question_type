import asyncio

import pytest
from pydantic import ValidationError

from services.assertion_service.generator import LLMAssertion, _validate_selector_tokens


def test_structured_assertion_contract_accepts_supported_values():
    assertion = LLMAssertion.model_validate({
        "order": 1,
        "group_id": "counter",
        "execution_mode": "sequential",
        "trigger": "click",
        "trigger_selector": "#increment",
        "input_value": None,
        "check_type": "text_content",
        "check_selector": "#count",
        "property_name": None,
        "operator": "equals",
        "expected_value": None,
        "points": 10,
        "is_sample": False,
        "wait_ms": 0,
        "sequence_order": 1,
    })
    assert assertion.check_type == "text_content"


def test_contract_rejects_visual_and_free_text_fields():
    with pytest.raises(ValidationError):
        LLMAssertion.model_validate({
            "order": 1,
            "execution_mode": "isolated",
            "trigger": "page_load",
            "check_type": "visual_region",
            "check_selector": "#card",
            "operator": "equals",
            "expected_result": "looks good",
        })


def test_selector_guard_rejects_invented_id():
    with pytest.raises(ValueError, match="not explicitly named"):
        _validate_selector_tokens(
            [{"trigger": "click", "trigger_selector": "#invented", "check_type": "text_content", "check_selector": "#count"}],
            "Click #increment and update #count.",
            '<button id="increment"></button><span id="count"></span>',
        )


def test_selector_guard_rejects_reference_only_hidden_id():
    with pytest.raises(ValueError, match="not explicitly named"):
        _validate_selector_tokens(
            [{"trigger": "page_load", "check_type": "text_content", "check_selector": "#secret"}],
            "Show the required message.",
            '<span id="secret">Done</span>',
        )


def test_generation_validation_rejects_hidden_selector_contract(monkeypatch):
    from services.assertion_service import generator

    async def fake_call_llm_structured(**kwargs):
        assert "EXPLICIT_SELECTOR_CONTRACT" in kwargs["system_prompt"]
        return {
            "status": "failed",
            "issues": [
                {
                    "type": "hidden_selector_contract",
                    "message": "Reference uses #secret but the question never names it.",
                }
            ],
        }

    monkeypatch.setattr(generator, "call_llm_structured", fake_call_llm_structured)

    with pytest.raises(ValueError, match="hidden_selector_contract"):
        asyncio.run(
            generator.validate_question_for_generation(
                "Hidden selector",
                "Show the required message.",
                '<span id="secret">Done</span>',
                "",
                "",
            )
        )
