import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

class TriggerType(str, Enum):
    PAGE_LOAD = "page_load"
    CLICK = "click"
    HOVER = "hover"
    INPUT = "input"
    CHANGE = "change"

class CheckType(str, Enum):
    DOM_PRESENCE = "dom_presence"
    ATTRIBUTE = "attribute"
    TEXT_CONTENT = "text_content"
    COMPUTED_STYLE = "computed_style"
    FUNCTION_PRESENCE = "function_presence"
    VISUAL_REGION = "visual_region"

@dataclass
class Assertion:
    id: str
    trigger: TriggerType
    check_type: CheckType
    trigger_selector: Optional[str] = None
    check_selector: Optional[str] = None
    property_name: Optional[str] = None
    expected_value: Optional[str] = None
    input_value: Optional[str] = None
    points: int = 0
    group_id: Optional[str] = None
    sequence_order: Optional[int] = None

@dataclass
class AssertionResult:
    assertion_id: str
    status: str
    reason: Optional[str]
    expected: Optional[str]
    actual: Optional[str]
    points_awarded: int
    message: str

@dataclass
class SubmissionResult:
    assertion_results: list = field(default_factory=list)
    total_points: int = 0
    max_points: int = 0
    console_errors: list = field(default_factory=list)

    @property
    def score_pct(self) -> float:
        return round(100 * self.total_points / self.max_points, 1) if self.max_points else 0.0

IFRAME_SELECTOR = "#candidate-preview"
ELEMENT_WAIT_MS = 3000
POLL_INTERVAL_MS = 100
MAX_SETTLE_WAIT_MS = 3000
INFINITE_LOOP_GUARD_MS = 1500

def selector_for_locator(selector: str) -> str:
    return selector.replace("\n", "").strip()

def build_sandboxed_srcdoc(html: str, css: str, js: str) -> str:
    guarded_js = f"""
    (function() {{
        try {{
            {js}
        }} catch (e) {{
            window.__candidateError = (e && e.message) ? e.message : String(e);
        }}
    }})();
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
{html}
<script>{guarded_js}</script>
</body>
</html>"""

class CandidateEvaluator:
    BOOLEAN_ATTRS = {"disabled", "checked", "readonly", "required", "hidden", "multiple", "selected", "autofocus"}
    COLOR_PROPS = {"color", "background-color", "border-color", "outline-color"}
    LENGTH_PROPS = {"width", "height", "margin", "padding", "top", "left", "font-size", "bottom", "right"}
    def __init__(self, page: Page):
        self.page = page
        self.console_errors: list = []
        self._register_console_listener()

    def _register_console_listener(self):
        def on_console(msg):
            if msg.type == "error":
                self.console_errors.append(msg.text)
        self.page.on("console", on_console)

    def load_candidate(self, html: str, css: str, js: str) -> None:
        self.html, self.css, self.js = html, css, js
        self._is_fresh_page = True
        # Create a host page with an iframe
        self.page.set_content(f'<!DOCTYPE html><html><head><style>iframe{{width:100vw;height:100vh;border:none;}}</style></head><body><iframe id="candidate-preview"></iframe></body></html>')
        srcdoc = build_sandboxed_srcdoc(html, css, js)
        
        # Inject srcdoc safely
        self.page.evaluate(
            "([sel, doc]) => document.querySelector(sel).srcdoc = doc",
            [IFRAME_SELECTOR, srcdoc]
        )
        self.page.wait_for_timeout(500)  # let the iframe finish (re)loading

    def _frame(self):
        return self.page.frame_locator(IFRAME_SELECTOR)

    def _run_trigger(self, assertion: Assertion) -> Optional[str]:
        if assertion.trigger == TriggerType.PAGE_LOAD:
            if getattr(self, "_is_fresh_page", False) is False:
                self.load_candidate(getattr(self, "html", ""), getattr(self, "css", ""), getattr(self, "js", ""))
            self._is_fresh_page = False
            return None

        self._is_fresh_page = False
        trigger_sel = assertion.trigger_selector or ""
        selector = selector_for_locator(trigger_sel)
        locator = self._frame().locator(selector).first

        try:
            locator.wait_for(state="visible", timeout=ELEMENT_WAIT_MS)
        except PlaywrightTimeoutError:
            return "element_not_found"

        try:
            if assertion.trigger == TriggerType.CLICK:
                locator.click(timeout=1000)
            elif assertion.trigger == TriggerType.HOVER:
                locator.hover(timeout=1000)
            elif assertion.trigger == TriggerType.INPUT:
                locator.fill(assertion.input_value or "test", timeout=1000)
            elif assertion.trigger == TriggerType.CHANGE:
                # Playwright's fill dispatches input, but not always change if not blurred
                locator.fill(assertion.input_value or "test", timeout=1000)
                locator.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
        except Exception as e:
            return f"trigger_failed:{e}"

        return None

    def _read_actual(self, assertion: Assertion) -> Any:
        if assertion.check_type == CheckType.FUNCTION_PRESENCE:
            fn_name = (assertion.check_selector or "").strip()
            return self.page.evaluate(
                """([iframeSel, fnName]) => {
                    const iframe = document.querySelector(iframeSel);
                    const win = iframe && iframe.contentWindow;
                    return !!(win && typeof win[fnName] === 'function');
                }""",
                [IFRAME_SELECTOR, fn_name],
            )

        check_sel = assertion.check_selector or ""
        selector = selector_for_locator(check_sel)
        locator = self._frame().locator(selector).first

        if assertion.check_type == CheckType.DOM_PRESENCE:
            return locator.count() > 0
        if assertion.check_type == CheckType.ATTRIBUTE:
            return locator.get_attribute(assertion.property_name or "", timeout=1000)
        if assertion.check_type == CheckType.TEXT_CONTENT:
            return (locator.inner_text(timeout=1000) or "").strip()
        if assertion.check_type == CheckType.COMPUTED_STYLE:
            return locator.evaluate(
                "(el, prop) => getComputedStyle(el).getPropertyValue(prop)",
                assertion.property_name,
            )

        raise ValueError(f"Unsupported check_type: {assertion.check_type}")

    def _canonicalize_via_browser(self, css_property: str, raw_value: str) -> str:
        try:
            return self._frame().locator("body").evaluate(
                """(body, [prop, val]) => {
                    const document = body.ownerDocument;
                    const probe = document.createElement('div');
                    probe.style[prop] = val;
                    body.appendChild(probe);
                    const computed = window.getComputedStyle(probe)[prop];
                    probe.remove();
                    return computed;
                }""",
                [css_property, str(raw_value)]
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                "canonicalize_via_browser_failed",
                extra={"property": css_property, "value": raw_value, "error": str(e), "traceback": True}
            )
            return str(raw_value).strip().lower()

    def _extract_number(self, v: str):
        m = re.fullmatch(r"-?\d+(\.\d+)?\s*(px|em|rem|%|deg|s|ms)?", v)
        return float(m.group(0).split()[0].rstrip("pxemr%dgs")) if m else None

    def _parse_rgba(self, v: str):
        m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", v)
        if not m:
            return None
        return [float(x) if x is not None else 1.0 for x in m.groups()]

    def _values_equivalent(self, a: str, b: str, tolerance: float = 0.5) -> bool:
        if not a or not b: return False
        a, b = str(a).strip().lower(), str(b).strip().lower()
        if a == b: return True

        num_a, num_b = self._extract_number(a), self._extract_number(b)
        if num_a is not None and num_b is not None:
            return abs(num_a - num_b) <= tolerance

        rgba_a, rgba_b = self._parse_rgba(a), self._parse_rgba(b)
        if rgba_a and rgba_b:
            if not all(abs(x - y) <= 1 for x, y in zip(rgba_a[:3], rgba_b[:3])):
                return False
            return abs(rgba_a[3] - rgba_b[3]) <= 0.01

        return False

    def _is_style_match(self, prop: str, actual: str, expected_canonical: str) -> bool:
        if prop in self.COLOR_PROPS or prop in self.LENGTH_PROPS:
            return self._values_equivalent(actual, expected_canonical, tolerance=0.5)
        return str(actual).strip().lower() == str(expected_canonical).strip().lower()

    def _is_match(self, actual: Any, expected: Any, property_name: str = None) -> bool:
        if property_name and property_name.lower() in self.BOOLEAN_ATTRS:
            expected_present = str(expected).strip().lower() in ("true", "yes", "1", "")
            actual_present = actual is not None and str(actual).lower() != "false"
            return actual_present == expected_present

        if actual is None:
            return False
        
        a = str(actual).strip().lower()
        e = str(expected).strip().lower()
        return a == e or e in a

    def _poll_until_match(self, assertion: Assertion) -> Any:
        elapsed = 0
        last_value = None
        
        expected_canonical = assertion.expected_value
        if assertion.check_type == CheckType.COMPUTED_STYLE and assertion.property_name:
            expected_canonical = self._canonicalize_via_browser(assertion.property_name, str(assertion.expected_value))
            
        while elapsed <= MAX_SETTLE_WAIT_MS:
            last_value = self._read_actual(assertion)
            
            if assertion.check_type == CheckType.COMPUTED_STYLE and assertion.property_name:
                is_match = self._is_style_match(assertion.property_name, str(last_value), expected_canonical)
            else:
                is_match = self._is_match(last_value, assertion.expected_value, assertion.property_name)
                
            if is_match:
                return last_value
            time.sleep(POLL_INTERVAL_MS / 1000)
            elapsed += POLL_INTERVAL_MS
        return last_value

    def evaluate_assertion(self, assertion: Assertion) -> AssertionResult:
        trigger_error = self._run_trigger(assertion)
        if trigger_error:
            return AssertionResult(
                assertion_id=assertion.id, status="FAIL", reason=trigger_error,
                expected=assertion.expected_value, actual=None, points_awarded=0,
                message=self._explain(assertion, trigger_error, None),
            )

        try:
            if assertion.check_type in (CheckType.DOM_PRESENCE, CheckType.FUNCTION_PRESENCE):
                actual = self._read_actual(assertion)
                passed = bool(actual) == (str(assertion.expected_value).lower() == "true" or str(assertion.expected_value).lower() == "element should exist" or not assertion.expected_value)
                # Note: original code checks == "true", but in DB we use descriptive strings like "Element should exist"
                if assertion.check_type == CheckType.DOM_PRESENCE and actual is True:
                    passed = True
            else:
                actual = self._poll_until_match(assertion)
                if assertion.check_type == CheckType.COMPUTED_STYLE and assertion.property_name:
                    expected_canonical = self._canonicalize_via_browser(assertion.property_name, str(assertion.expected_value))
                    passed = self._is_style_match(assertion.property_name, str(actual), expected_canonical)
                else:
                    passed = self._is_match(actual, assertion.expected_value, assertion.property_name)
        except Exception as e:
            return AssertionResult(
                assertion_id=assertion.id, status="ERROR", reason="check_execution_failed",
                expected=assertion.expected_value, actual=None, points_awarded=0,
                message=f"Could not evaluate the check: {e}",
            )

        status = "PASS" if passed else "FAIL"
        return AssertionResult(
            assertion_id=assertion.id, status=status,
            reason=None if passed else "value_mismatch",
            expected=assertion.expected_value, actual=str(actual) if actual is not None else None,
            points_awarded=assertion.points if passed else 0,
            message=self._explain(assertion, None if passed else "value_mismatch", actual),
        )

    def _explain(self, assertion: Assertion, reason: Optional[str], actual: Any) -> str:
        if reason == "element_not_found":
            # "element_not_found" is only returned by _run_trigger, meaning the trigger selector failed.
            return f"Trigger element '{(assertion.trigger_selector or '')}' was not found or not visible in the submitted code."
        if reason and reason.startswith("trigger_failed"):
            return f"The {assertion.trigger.value} action could not be performed: {reason.split(':', 1)[1][:100]}"
        if reason == "value_mismatch":
            label = assertion.property_name or assertion.check_type.value
            return f"Expected {label} '{assertion.expected_value}' but got '{actual}'."
        if reason == "check_execution_failed":
            return "The check could not be evaluated due to an internal error."
        return "Passed."

    def evaluate_submission(
        self, html: str, css: str, js: str, assertions: list
    ) -> SubmissionResult:
        result = SubmissionResult(max_points=sum(a.points for a in assertions))
        
        # Partition into groups. Default to sequential 'default_flow' unless explicitly isolated.
        groups = {}
        for a in assertions:
            is_isolated = getattr(a, "execution_mode", "") == "isolated"
            key = f"__solo_{a.id}" if is_isolated else (getattr(a, "group_id", None) or "default_flow")
            if key not in groups:
                groups[key] = []
            groups[key].append(a)

        for group_id, group_assertions in groups.items():
            self.load_candidate(html, css, js)  # Fresh page ONCE per group
            
            # Sort group's assertions by sequence_order if they have it
            group_assertions.sort(key=lambda x: x.sequence_order or 0)
            
            for assertion in group_assertions:
                ar = self.evaluate_assertion(assertion)
                result.assertion_results.append(ar)
                result.total_points += ar.points_awarded

        # Re-sort assertion results back to the original input order so the UI matches
        order_map = {a.id: i for i, a in enumerate(assertions)}
        result.assertion_results.sort(key=lambda r: order_map.get(r.assertion_id, 0))

        result.console_errors = list(self.console_errors)
        return result
