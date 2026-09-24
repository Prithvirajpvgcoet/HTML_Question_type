import re
import asyncio
from playwright.sync_api import sync_playwright
from services.evaluation_service.evaluator import (
    CandidateEvaluator, Assertion, TriggerType, CheckType
)

def parse_expected_result(check_type: str, expected_result: str) -> tuple[str | None, str]:
    """
    Parses 'type: password', 'value=testuser', 'text: Log in', 'background-color: red'
    into (property_name, expected_value) — tolerant of ':' or '=' as the delimiter.
    """
    raw = str(expected_result).strip() if expected_result else ""
    match = re.match(r'^([\w\-]+)\s*[:=]\s*(.*)$', raw)
    if not match:
        return None, raw

    prop, value = match.group(1), match.group(2).strip()

    if check_type in ("computed_style", "attribute"):
        return prop, value
    if check_type == "text_content" and prop.lower() in ("text", "content", "text_content", "textcontent"):
        return None, value          # strip the label, keep the real expected text
    return None, raw

def _run_sync_evaluation(html: str, css: str, js: str, assertions: list) -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security"
            ]
        )
        context = browser.new_context(
            java_script_enabled=True,
            offline=True
        )
        page = context.new_page()
        
        # Block network for security
        page.route("**/*", lambda route: route.abort())
        
        evaluator = CandidateEvaluator(page)
        
        # We need to map dict assertions back into the evaluator's Assertion dataclass
        dataclass_assertions = []
        for a in assertions:
            expected_raw = a.get("expected_result", "")
            check_type_str = a.get("check_type", "dom_presence")
            
            prop_name, expected = parse_expected_result(check_type_str, expected_raw)
            
            dataclass_assertions.append(Assertion(
                id=a.get("id", "temp"),
                trigger=TriggerType(a.get("trigger", "page_load")),
                trigger_selector=a.get("trigger_selector", ""), check_selector=a.get("check_selector", ""),
                check_type=CheckType(check_type_str),
                property_name=prop_name.strip() if prop_name else None,
                expected_value=expected.strip() if expected else expected,
                input_value="test",
                points=a.get("points", 0),
                group_id=a.get("group_id"),
                sequence_order=a.get("sequence_order")
            ))

        try:
            submission_result = evaluator.evaluate_submission(html, css, js, dataclass_assertions)
            
            # Map SubmissionResult back to the list format the API expects
            # (which is {"assertion_id": "...", "passed": True, "actual_value": "...", "error": "...", "points_awarded": ...})
            results = []
            for ar in submission_result.assertion_results:
                results.append({
                    "assertion_id": ar.assertion_id,
                    "passed": ar.status == "PASS",
                    "actual_value": ar.actual or "",
                    "error": ar.message if ar.status != "PASS" else "",
                    "points_awarded": ar.points_awarded
                })
            return results
        finally:
            context.close()
            browser.close()

async def evaluate_submission(html: str, css: str, js: str, assertions: list) -> list:
    # Serialize SQLAlchemy models into plain dicts
    serialized_assertions = []
    for a in assertions:
        serialized_assertions.append({
            "id": getattr(a, "id", None),
            "trigger": getattr(a, "trigger", None),
            "trigger_selector": getattr(a, "trigger_selector", ""), "check_selector": getattr(a, "check_selector", ""),
            "check_type": getattr(a, "check_type", None),
            "expected_result": getattr(a, "expected_result", ""),
            "wait_ms": getattr(a, "wait_ms", 0),
            "points": getattr(a, "points", 0),
            "group_id": getattr(a, "group_id", None),
            "sequence_order": getattr(a, "sequence_order", None)
        })
        
    return await asyncio.to_thread(
        _run_sync_evaluation, 
        html, 
        css, 
        js, 
        serialized_assertions
    )
