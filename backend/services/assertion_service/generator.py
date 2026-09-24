from config import settings
import json
import re
from ai.llm_client.client import call_llm_structured
from pydantic import BaseModel, Field
from typing import Literal, Optional

class LLMAssertion(BaseModel):
    trigger: Literal["page_load", "click", "input", "change", "hover"]
    trigger_selector: Optional[str] = Field(default=None)
    check_selector: str
    wait_ms: int = Field(default=300)
    check_type: Literal["dom_presence", "computed_style", "attribute", "text_content", "visual_region"]
    expected_result: str
    points: int = 5
    execution_mode: Literal["isolated", "sequential"] = "sequential"
    group_id: Optional[str] = Field(default=None)
    sequence_order: Optional[int] = Field(default=1)

class AssertionList(BaseModel):
    assertions: list[LLMAssertion]

PROMPT = """You are a test automation engineer generating UI assertions for an HTML/CSS/JS coding question on an assessment platform.

Your task: Generate a complete, ORDERED set of UI assertions that cover the full interaction sequence:
  1. Initial page load state
  2. Each intermediate user interaction step (clicks, inputs, changes, hovers)
  3. Every distinct behavior stated in the description — including style states, pseudo-states (:hover, :disabled), and timed/delayed state changes
  4. The final expected visual/DOM state after all interactions

Before generating assertions, silently enumerate every distinct testable requirement in the description as a checklist (one line per requirement). Then generate at least one assertion per checklist item.

CRITICAL SCHEMA RULES (DO NOT IGNORE):
1. DISTINCT TARGETS: You must explicitly define BOTH the `trigger_selector` (the interactive element) AND the `check_selector` (the element to validate).
2. EXECUTION MODE & GROUPING (CRITICAL):
   - If checking an element's state or interactivity depends on prior user actions (e.g., a button that's only enabled once other fields are filled, or a UI state reachable only after a click), you MUST chain ALL assertions needed to reach and verify that state into the SAME `group_id`, ordered by `sequence_order`.
   - Each group starts from a blank page reload — nothing from outside the group carries over.
   - Independent, order-agnostic checks (e.g., verifying initial page load structure) should omit `group_id` (null) and use `execution_mode: isolated`.
   - A `hover` or `click` trigger assertion that targets an element gated by other input state MUST be preceded, within the SAME group, by the setup steps (`input`/`change` assertions) that satisfy that gate.
3. EXPECTED RESULT: `computed_style` must be `property: value`. `attribute` must be `attribute=value`. `dom_presence` must be `present` or `absent`.

TESTING BEHAVIOR RULES:
- Prefer IDs like #colorBtn, #shape. Never use class names unless the question requires them.
- Use conservative wait_ms: static DOM=0-100, CSS transitions=500-1500, JS timers=2000-5000.
- CSS properties MUST use check_type "computed_style".
- :hover or :disabled states MUST include a trigger step immediately before the check.
- SEQUENCING & PRECONDITIONS: If an element (like a button) is disabled by default, you MUST use execution_mode: "sequential" and generate prerequisite assertions that fill required inputs to enable it BEFORE generating assertions that hover or click it.
- MULTI-FIELD PRECONDITION RULE (MANDATORY — READ REFERENCE JS BEFORE WRITING ANY CONDITIONAL CHECK):
  Before writing ANY assertion that checks a derived/conditional UI state
  (e.g. button enabled/disabled, class toggled, error message shown, section revealed),
  you MUST follow these steps in order:
    Step 1: Read the Reference JS code provided in the user message. Locate the EXACT
            condition (if-statement, ternary, or logical expression) that controls that state.
    Step 2: List EVERY input field whose .value, .checked, or .files.length is READ
            inside that condition. Count them carefully.
            Example: "username.value !== '' && password.value !== ''" has TWO fields.
    Step 3: Generate exactly ONE setup assertion (trigger: "input" or "change") per field
            found in Step 2. Place ALL setup assertions in the same group_id, with
            ascending sequence_order values, BEFORE the assertion that checks the derived state.
  RULE: Number of setup assertions = Number of fields in the JS condition. Never fewer.
  WRONG (one precondition for a two-field condition — this will always fail):
    [{"trigger":"input","trigger_selector":"#username","group_id":"g1","sequence_order":1},
     {"trigger":"page_load","check_selector":"#loginBtn","expected_result":"disabled=false","group_id":"g1","sequence_order":2}]
  CORRECT (one precondition per field — this will pass):
    [{"trigger":"input","trigger_selector":"#username","group_id":"g1","sequence_order":1},
     {"trigger":"input","trigger_selector":"#password","group_id":"g1","sequence_order":2},
     {"trigger":"page_load","check_selector":"#loginBtn","expected_result":"disabled=false","group_id":"g1","sequence_order":3}]
- Delayed/timed changes MUST be a separate assertion with wait_ms matching the delay.
- Generate EXACTLY 6 assertions. If there are more than 6 testable requirements, combine related checks into a single assertion (e.g., verifying multiple style changes after a click) or prioritize the most critical functional behaviors to stay at exactly 6.
- Mark exactly the first half (rounded down) of assertions, in generation order, as "is_sample": true (visible to candidate); remainder false.
- Order assertions from page load to final state.

Respond ONLY with this JSON object:
{
  "assertions": [
    {
      "order": 1,
      "trigger": "page_load" | "click" | "change" | "input" | "hover",
      "trigger_selector": "CSS selector",
      "check_type": "dom_presence" | "computed_style" | "text_content" | "attribute" | "visual_region",
      "check_selector": "CSS selector",
      "expected_result": "property: value, attribute=value, or present/absent",
      "wait_ms": 0,
      "points": 10,
      "is_sample": false,
      "execution_mode": "isolated",
      "group_id": null,
      "sequence_order": null,
      "depends_on_state": null
    }
  ]
}
"""

async def generate_assertions_from_llm(title: str, description: str, html: str, css: str, js: str):
    html = html or ""
    css = css or ""
    js = js or ""
    # Pre-parse valid IDs and Classes from the reference HTML to use as a guardrail
    valid_ids = set(re.findall(r'id=["']([^"']+)["']', html))
    valid_classes = set(c for match in re.findall(r'class=["']([^"']+)["']', html) for c in match.split())
    
    # Inject explicit allowed lists into the prompt
    allowed_ids_str = ", ".join([f"#{i}" for i in valid_ids]) if valid_ids else "None"
    allowed_classes_str = ", ".join([f".{c}" for c in valid_classes]) if valid_classes else "None"
    
    user_content = f"Question Title: {title}
Question Description: {description}

Reference HTML:
{html}

Reference CSS:
{css}

Reference JS:
{js}

"
    user_content += "CRITICAL: You may ONLY use the following specific selectors found in the reference code:
"
    user_content += f"ALLOWED IDs: {allowed_ids_str}
ALLOWED CLASSES: {allowed_classes_str}

"

    try:
        # Schema-enforced LLM call with built-in retries and rate limiting
        result = await call_llm_structured(
            system_prompt=PROMPT,
            user_message=user_content,
            schema=AssertionList,
            model=settings.llm_model_generation,
            thinking_level="low"
        )
        
        # Result is already a parsed dictionary thanks to call_llm_structured
        assertions = result.get("assertions", [])
        
        # Guardrail check
        is_valid = True
        for a in assertions:
            combined_selectors = (a.get('trigger_selector') or '') + ' ' + (a.get('check_selector') or '')
            
            # Check IDs
            ids_in_selector = re.findall(r'#([a-zA-Z0-9_-]+)', combined_selectors)
            for id_sel in ids_in_selector:
                if id_sel not in valid_ids:
                    print(f"Guardrail failed: ID '{id_sel}' not found in reference HTML.")
                    is_valid = False
                    
            # Check Classes
            classes_in_selector = re.findall(r'\.([a-zA-Z0-9_-]+)', combined_selectors)
            for cls_sel in classes_in_selector:
                if cls_sel not in valid_classes:
                    print(f"Guardrail failed: Class '{cls_sel}' not found in reference HTML.")
                    is_valid = False
                    
        if not is_valid:
            print("Warning: Guardrail warnings detected, but returning assertions anyway (Gemini schema usually mitigates worst offenses).")
            
    except Exception as e:
        print(f"generate_assertions_from_llm failed: {e}")
        raise e

    # Enforce max 6 assertions
    assertions = assertions[:6]

    # Re-distribute points dynamically based on difficulty to enforce consistency
    def get_weight(trigger, check_type):
        if trigger == "page_load" and check_type == "dom_presence":
            return 1 # Easy
        if trigger in ("click", "input", "change", "hover") and check_type == "computed_style":
            return 3 # Hard
        return 2 # Medium

    weights = [get_weight(a.get("trigger", "page_load"), a.get("check_type", "dom_presence")) for a in assertions]
    total_weight = sum(weights)
    
    if total_weight > 0 and len(assertions) > 0:
        running = 0
        for i, a in enumerate(assertions):
            if i < len(assertions) - 1:
                pts = round((weights[i] / total_weight) * 50)
                a["points"] = pts
                running += pts
            else:
                a["points"] = 50 - running

    return assertions


async def generate_edge_cases_from_llm(title: str, description: str, existing_assertions: list) -> list:
    edge_prompt = f"""
    Based on the {len(existing_assertions)} assertions already created for '{title}', generate 2 additional edge case assertions 
    that would catch common candidate mistakes (e.g. empty/null values, wrong types, extreme values).
    Description: {description}
    """
    try:
        result = await call_llm_structured(
            system_prompt="You are an edge-case generation AI. Generate edge cases.",
            user_message=edge_prompt,
            schema=AssertionList,
            model=settings.llm_model_generation,
            thinking_level="low"
        )
        return result.get("assertions", [])[:2]
    except Exception as e:
        print(f"Edge Case Generator Error: {e}")
        return []
    except Exception as e:
        print(f"Edge Case Generator Error: {e}")
        return []

