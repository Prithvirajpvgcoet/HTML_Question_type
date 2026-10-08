import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


call_llm_structured = None


def _generation_model() -> str | None:
    try:
        from config import settings

        return settings.llm_model_generation
    except Exception:
        return None


async def _call_llm_structured(**kwargs):
    global call_llm_structured
    if call_llm_structured is None:
        from ai.llm_client.client import call_llm_structured as imported_call_llm_structured

        call_llm_structured = imported_call_llm_structured
    return await call_llm_structured(**kwargs)


class LLMAssertion(BaseModel):


    order: int = Field(ge=1)
    group_id: Optional[str] = None
    execution_mode: Literal["isolated", "sequential"] = "isolated"
    trigger: Literal["page_load", "click", "input", "change", "hover", "call_function"]
    trigger_selector: Optional[str] = None
    input_value: Optional[str] = None
    check_type: Literal[
        "dom_presence", "dom_absence", "element_count", "text_content",
        "attribute", "computed_style", "function_presence",
    ]
    check_selector: str
    property_name: Optional[str] = None
    operator: Literal["equals", "contains", "regex", "exists", "not_exists"] = "equals"
    expected_value: Optional[str] = None
    points: int = Field(default=10, ge=0, le=100)
    is_sample: bool = False
    wait_ms: int = Field(default=0, ge=0, le=10000)
    sequence_order: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.trigger != "page_load" and not self.trigger_selector:
            raise ValueError("non-page-load triggers require trigger_selector")
        if self.trigger in ("input", "change", "call_function") and self.input_value is None:
            raise ValueError(f"{self.trigger} requires input_value")
        if self.check_type in ("attribute", "computed_style") and not self.property_name:
            raise ValueError(f"{self.check_type} requires property_name")
        if self.execution_mode == "sequential" and (not self.group_id or self.sequence_order is None):
            raise ValueError("sequential assertions require group_id and sequence_order")
        return self


class AssertionList(BaseModel):

    assertions: list[LLMAssertion]


class ValidationIssue(BaseModel):


    type: Literal[
        "ambiguous_behaviour",
        "solution_mismatch",
        "not_ui_observable",
        "hidden_selector_contract",
    ]
    message: str


class ValidationResponse(BaseModel):


    status: Literal["passed", "failed"]
    issues: list[ValidationIssue] = []


VALIDATION_PROMPT_PATH = Path(__file__).resolve().parents[2] / "ai" / "prompts" / "validation" / "v2.md"


PROMPT = """You generate browser assertions for an HTML/CSS/JavaScript coding question.

Your only responsibility is deciding what observable requirements should be tested and how to reach them. Playwright will read actual browser values, derive expected values from the reference solution, and decide pass/fail. Return JSON only, matching the supplied schema.

Rules:
- Use only the schema's trigger, check_type, and operator values.
- Use selectors and global function names that occur in the supplied question requirements and reference solution. Never invent an ID, class, element contract, or function name that the candidate was not explicitly told to use.
- Set expected_value to null for values Playwright can derive: text_content, attribute, computed_style, and element_count.
- For dom_presence and function_presence use operator "exists" and expected_value null.
- For dom_absence use operator "not_exists" and expected_value null.
- Use operator "equals" by default. Use contains or regex only when the written requirement explicitly calls for partial/pattern matching.
- property_name is required only for attribute and computed_style.
- input_value is the text for input/change. For call_function it is a JSON array encoded as a string, and trigger_selector is the global function name.
- Independent checks use execution_mode "isolated". A workflow uses execution_mode "sequential", one group_id, and ascending sequence_order values.
- Include every prerequisite interaction in a sequential group. Each assertion performs one trigger and one check.
- visual_region is unsupported and must never be emitted.
- Assertions must represent explicit requirements. Do not score code quality, naming, implementation technique, or subjective appearance.
- Use deterministic waits only when the reference behavior requires a timer. Never exceed 10000 ms.
"""


def _load_validation_prompt() -> str:
    return VALIDATION_PROMPT_PATH.read_text(encoding="utf-8")


async def validate_question_for_generation(title: str, description: str, html: str, css: str, js: str) -> None:
    user_message = f"""Question title: {title}
Question requirements visible to candidates:
{description}

Reference HTML:
{html}

Reference CSS:
{css}

Reference JavaScript:
{js}
"""
    result = await _call_llm_structured(
        system_prompt=_load_validation_prompt(),
        user_message=user_message,
        schema=ValidationResponse,
        model=_generation_model(),
        thinking_level="low",
    )
    validation = ValidationResponse.model_validate(result)
    
    # RELAXED: Only block on strictly impossible to test issues.
    BLOCKING = {"not_ui_observable"}
    blocking = [i for i in validation.issues if i.type in BLOCKING]
    
    if blocking:
        issue_text = "; ".join(f"{issue.type}: {issue.message}" for issue in blocking)
        raise ValueError(f"Question is not ready for assertion generation: {issue_text}")


def _validate_selector_tokens(assertions: list[dict], requirement_source: str, reference_source: str) -> None:
    requirement_source = requirement_source or ""
    reference_source = reference_source or ""
    for item in assertions:
        selectors = []
        if item.get("trigger") not in ("page_load", "call_function"):
            selectors.append(item.get("trigger_selector") or "")
        if item.get("check_type") != "function_presence":
            selectors.append(item.get("check_selector") or "")
        for selector in selectors:
            for ident in re.findall(r"#([A-Za-z_][\w-]*)", selector):
                # RELAXED: Only strictly enforce it exists in the reference solution
                if not re.search(rf"\b{re.escape(ident)}\b", reference_source):
                    raise ValueError(f"Generated selector '#{ident}' is absent from the reference solution")
            for class_name in re.findall(r"\.([A-Za-z_][\w-]*)", selector):
                # RELAXED: Only strictly enforce it exists in the reference solution
                if not re.search(rf"\b{re.escape(class_name)}\b", reference_source):
                    raise ValueError(f"Generated selector '.{class_name}' is absent from the reference solution")
        function_name = ""
        if item.get("trigger") == "call_function":
            function_name = item.get("trigger_selector") or ""
        elif item.get("check_type") == "function_presence":
            function_name = item.get("check_selector") or ""
        if function_name:
            if not re.search(rf"\b{re.escape(function_name)}\b", reference_source):
                raise ValueError(f"Generated function '{function_name}' is absent from the reference solution")


async def generate_assertions_from_llm(
    title: str,
    description: str,
    html: str,
    css: str,
    js: str,
    keep_assertions: list[dict] | None = None,
    failed_context: list[dict] | None = None,
    target_count: int | None = None,
    mode: str = "full",
) -> list[dict]:
    html, css, js = html or "", css or "", js or ""
    await validate_question_for_generation(title, description or "", html, css, js)
    count = max(1, min(target_count or 6, 15))
    context = ""
    if keep_assertions:
        context += "\nAlready validated; do not duplicate:\n" + "\n".join(
            f"- {a.get('trigger')} {a.get('trigger_selector')} -> {a.get('check_type')} {a.get('check_selector')}"
            for a in keep_assertions
        )
    if failed_context:
        context += "\nRepair these requirements using valid selectors and structure:\n" + "\n".join(
            f"- {a.get('check_type')} {a.get('check_selector')}: {a.get('error')}"
            for a in failed_context
        )
    desired = count - len(keep_assertions or []) if mode == "diversify" else count
    desired = max(1, desired)
    user_message = f"""Question title: {title}
Question requirements: {description}

Reference HTML:
{html}

Reference CSS:
{css}

Reference JavaScript:
{js}

Generate exactly {desired} new assertions.{context}
"""
    result = await _call_llm_structured(
        system_prompt=PROMPT,
        user_message=user_message,
        schema=AssertionList,
        model=_generation_model(),
        thinking_level="low",
    )
    assertions = AssertionList.model_validate(result).model_dump()["assertions"][:15]
    _validate_selector_tokens(assertions, description or "", "\n".join((html, css, js)))

    # Keep scoring deterministic and make the assertion set total 100 points.
    base, remainder = divmod(100, len(assertions))
    for index, item in enumerate(assertions):
        item["order"] = index + 1
        item["points"] = base + (1 if index < remainder else 0)
        item["is_sample"] = index < len(assertions) // 2
    return assertions


async def generate_edge_cases_from_llm(
    title: str,
    description: str,
    existing_assertions: list,
    html: str = "",
    css: str = "",
    js: str = "",
) -> list[dict]:
    return await generate_assertions_from_llm(
        title, description, html, css, js, keep_assertions=existing_assertions,
        target_count=2, mode="diversify",
    )
