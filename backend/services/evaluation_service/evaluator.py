import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


class TriggerType(str, Enum):
    PAGE_LOAD = "page_load"
    CLICK = "click"
    INPUT = "input"
    CHANGE = "change"
    HOVER = "hover"
    CALL_FUNCTION = "call_function"


class CheckType(str, Enum):
    DOM_PRESENCE = "dom_presence"
    DOM_ABSENCE = "dom_absence"
    ELEMENT_COUNT = "element_count"
    TEXT_CONTENT = "text_content"
    ATTRIBUTE = "attribute"
    COMPUTED_STYLE = "computed_style"
    FUNCTION_PRESENCE = "function_presence"


class Operator(str, Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


@dataclass
class Assertion:
    id: str
    trigger: TriggerType
    check_type: CheckType
    trigger_selector: Optional[str] = None
    check_selector: Optional[str] = None
    property_name: Optional[str] = None
    operator: Operator = Operator.EQUALS
    expected_value: Optional[str] = None
    input_value: Optional[str] = None
    points: int = 0
    group_id: Optional[str] = None
    sequence_order: Optional[int] = None
    execution_mode: str = "isolated"
    wait_ms: int = 0


@dataclass
class AssertionResult:
    assertion_id: str
    status: str
    reason: Optional[str]
    expected: Optional[str]
    actual: Optional[str]
    points_awarded: int
    message: str
    blocked_by: Optional[str] = None


@dataclass
class SubmissionResult:
    assertion_results: list[AssertionResult] = field(default_factory=list)
    total_points: int = 0
    max_points: int = 0
    console_errors: list[str] = field(default_factory=list)

    @property
    def score_pct(self) -> float:
        return round(100 * self.total_points / self.max_points, 1) if self.max_points else 0.0


IFRAME_SELECTOR = "#candidate-preview"
ACTION_TIMEOUT_MS = 500
POLL_INTERVAL_MS = 100
MAX_SETTLE_WAIT_MS = 3000


def build_sandboxed_srcdoc(html: str, css: str, js: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
*, *::before, *::after {{ animation-duration: 0s !important; animation-delay: 0s !important; transition-duration: 0s !important; }}
{css}
</style></head><body>{html}
<script>
try {{
  let __seed = 123456789;
  Math.random = () => ((__seed = (__seed * 16807) % 2147483647) - 1) / 2147483646;
  const __RealDate = Date;
  const __fixedEpoch = 1704067200000;
  Date = class extends __RealDate {{
    constructor(...args) {{ super(...(args.length ? args : [__fixedEpoch])); }}
    static now() {{ return __fixedEpoch; }}
  }};
  {js}
}} catch (error) {{ window.__candidateError = error?.message || String(error); }}
</script></body></html>"""


class CandidateEvaluator:
    def __init__(self, page: Page):
        self.page = page
        self.console_errors: list[str] = []
        self.page.on("console", lambda msg: self.console_errors.append(msg.text) if msg.type == "error" else None)

    def load_candidate(self, html: str, css: str, js: str) -> None:
        self.html, self.css, self.js = html, css, js
        self.page.set_content(
            '<!doctype html><html><body style="margin:0"><iframe id="candidate-preview" '
            'sandbox="allow-scripts allow-forms" style="width:100vw;height:100vh;border:0"></iframe></body></html>',
            wait_until="domcontentloaded",
        )
        self.page.locator(IFRAME_SELECTOR).evaluate(
            "(frame, source) => frame.srcdoc = source", build_sandboxed_srcdoc(html, css, js)
        )
        self._frame().locator("body").wait_for(state="attached", timeout=ACTION_TIMEOUT_MS)

    def _frame(self):
        return self.page.frame_locator(IFRAME_SELECTOR)

    def _run_trigger(self, assertion: Assertion) -> Optional[str]:
        if assertion.trigger == TriggerType.PAGE_LOAD:
            return None
        if assertion.trigger == TriggerType.CALL_FUNCTION:
            name = (assertion.trigger_selector or "").strip()
            if not re.fullmatch(r"[A-Za-z_$][\w$]*", name):
                return "invalid_function_name"
            try:
                args = json.loads(assertion.input_value or "[]")
                if not isinstance(args, list):
                    args = [args]
                self._frame().locator("body").evaluate(
                    "(body, data) => { const fn = body.ownerDocument.defaultView[data.name]; "
                    "if (typeof fn !== 'function') throw new Error('function not found'); return fn(...data.args); }",
                    {"name": name, "args": args},
                )
                return None
            except Exception as exc:
                return f"trigger_failed:{exc}"

        selector = (assertion.trigger_selector or "").replace("\n", "").strip()
        if not selector:
            return "missing_trigger_selector"
        locator = self._frame().locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
            if assertion.trigger == TriggerType.CLICK:
                locator.click(timeout=ACTION_TIMEOUT_MS)
            elif assertion.trigger == TriggerType.HOVER:
                locator.hover(timeout=ACTION_TIMEOUT_MS)
            elif assertion.trigger in (TriggerType.INPUT, TriggerType.CHANGE):
                locator.fill(assertion.input_value or "", timeout=ACTION_TIMEOUT_MS)
                if assertion.trigger == TriggerType.CHANGE:
                    locator.dispatch_event("change")
        except PlaywrightTimeoutError:
            return "trigger_element_not_found"
        except Exception as exc:
            return f"trigger_failed:{exc}"
        return None

    def _read_actual(self, assertion: Assertion) -> Any:
        if assertion.check_type == CheckType.FUNCTION_PRESENCE:
            name = (assertion.check_selector or "").strip()
            return self._frame().locator("body").evaluate(
                "(body, name) => typeof body.ownerDocument.defaultView[name] === 'function'", name
            )
        selector = (assertion.check_selector or "").replace("\n", "").strip()
        locator = self._frame().locator(selector)
        count = locator.count()
        
        if assertion.check_type == CheckType.DOM_PRESENCE:
            return count > 0
        if assertion.check_type == CheckType.DOM_ABSENCE:
            return count == 0
        if assertion.check_type == CheckType.ELEMENT_COUNT:
            return count
            
        # Fail fast if element missing for state checks
        if count == 0:
            return None
            
        first = locator.first
        
        if assertion.check_type == CheckType.TEXT_CONTENT:
            # Audit says whitespace should be normalized, not just stripped
            text = (first.text_content(timeout=ACTION_TIMEOUT_MS) or "")
            import re
            return re.sub(r"\s+", " ", text).strip()
        if assertion.check_type == CheckType.ATTRIBUTE:
            if not assertion.property_name:
                raise ValueError("attribute checks require property_name")
            if assertion.property_name == "value":
                return first.input_value(timeout=ACTION_TIMEOUT_MS)
            return first.get_attribute(assertion.property_name, timeout=ACTION_TIMEOUT_MS)
        if assertion.check_type == CheckType.COMPUTED_STYLE:
            if not assertion.property_name:
                raise ValueError("computed_style checks require property_name")
            return first.evaluate(
                "(element, propertyName) => getComputedStyle(element).getPropertyValue(propertyName).trim()",
                assertion.property_name,
            )
        raise ValueError(f"Unsupported check type: {assertion.check_type.value}")

    @staticmethod
    def _matches(actual: Any, expected: Any, operator: Operator) -> bool:
        if operator == Operator.EXISTS:
            return actual is not None and actual is not False
        if operator == Operator.NOT_EXISTS:
            return actual is None or actual is False
        actual_text = "" if actual is None else str(actual)
        expected_text = "" if expected is None else str(expected)
        if operator == Operator.EQUALS:
            return actual_text == expected_text
        if operator == Operator.CONTAINS:
            return expected_text in actual_text
        if operator == Operator.REGEX:
            return re.search(expected_text, actual_text) is not None
        return False

    def _assertion_matches(self, assertion: Assertion, actual: Any) -> bool:
        if assertion.check_type in (CheckType.DOM_PRESENCE, CheckType.FUNCTION_PRESENCE) and assertion.operator == Operator.EXISTS:
            return actual is True
        if assertion.check_type == CheckType.DOM_ABSENCE and assertion.operator == Operator.NOT_EXISTS:
            return actual is True
        return self._matches(actual, assertion.expected_value, assertion.operator)

    def evaluate_assertion(self, assertion: Assertion, capture_only: bool = False) -> AssertionResult:
        trigger_error = self._run_trigger(assertion)
        if trigger_error:
            return AssertionResult(assertion.id, "FAIL", trigger_error, assertion.expected_value, None, 0,
                                   f"Trigger failed: {trigger_error}")
        try:
            if assertion.wait_ms:
                self.page.wait_for_timeout(min(max(assertion.wait_ms, 0), 10000))
            deadline = min(max(assertion.wait_ms, MAX_SETTLE_WAIT_MS), 10000)
            elapsed = 0
            actual = self._read_actual(assertion)
            while not capture_only and not self._assertion_matches(assertion, actual) and elapsed < deadline:
                self.page.wait_for_timeout(POLL_INTERVAL_MS)
                elapsed += POLL_INTERVAL_MS
                actual = self._read_actual(assertion)
            passed = capture_only or self._assertion_matches(assertion, actual)
        except Exception as exc:
            return AssertionResult(assertion.id, "ERROR", "check_execution_failed", assertion.expected_value,
                                   None, 0, f"Check failed to execute: {exc}")
        actual_text = "" if actual is None else str(actual)
        return AssertionResult(
            assertion.id, "PASS" if passed else "FAIL", None if passed else "value_mismatch",
            assertion.expected_value, actual_text, assertion.points if passed and not capture_only else 0,
            "Passed." if passed else f"Expected {assertion.operator.value} '{assertion.expected_value}', got '{actual_text}'.",
        )

    def evaluate_submission(self, html: str, css: str, js: str, assertions: list[Assertion], capture_only: bool = False) -> SubmissionResult:
        result = SubmissionResult(max_points=sum(item.points for item in assertions))
        groups: dict[str, list[Assertion]] = {}
        for assertion in assertions:
            mode = assertion.execution_mode.value if hasattr(assertion.execution_mode, "value") else str(assertion.execution_mode)
            key = f"__isolated_{assertion.id}" if mode == "isolated" else (assertion.group_id or "__sequential_default")
            groups.setdefault(key, []).append(assertion)
        for group in groups.values():
            self.load_candidate(html, css, js)
            group.sort(key=lambda item: item.sequence_order if item.sequence_order is not None else 0)
            blocked_by: Optional[str] = None
            for assertion in group:
                if blocked_by:
                    ar = AssertionResult(assertion.id, "SKIPPED", "blocked", assertion.expected_value, None, 0,
                                         f"Blocked by assertion #{blocked_by}.", blocked_by=blocked_by)
                else:
                    ar = self.evaluate_assertion(assertion, capture_only=capture_only)
                    mode = assertion.execution_mode.value if hasattr(assertion.execution_mode, "value") else str(assertion.execution_mode)
                    if ar.status != "PASS" and mode == "sequential":
                        blocked_by = assertion.id
                result.assertion_results.append(ar)
                result.total_points += ar.points_awarded
        input_order = {item.id: index for index, item in enumerate(assertions)}
        result.assertion_results.sort(key=lambda item: input_order.get(item.assertion_id, 0))
        result.console_errors = list(self.console_errors)
        return result
