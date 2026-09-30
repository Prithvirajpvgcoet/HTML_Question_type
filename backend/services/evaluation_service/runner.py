import asyncio
import multiprocessing
from queue import Empty
from typing import Any

from playwright.sync_api import sync_playwright

from services.evaluation_service.evaluator import (
    Assertion,
    CandidateEvaluator,
    CheckType,
    Operator,
    TriggerType,
)


SUBMISSION_TIMEOUT_SECONDS = 30
FIXED_EPOCH_MS = 1704067200000


def _value(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    return value.value if hasattr(value, "value") else value


def serialize_assertion(item: Any) -> dict:
    if isinstance(item, dict):
        return dict(item)
    return {
        "id": getattr(item, "id", None),
        "trigger": _value(getattr(item, "trigger", None), "page_load"),
        "trigger_selector": getattr(item, "trigger_selector", None),
        "input_value": getattr(item, "input_value", None),
        "check_type": _value(getattr(item, "check_type", None), "dom_presence"),
        "check_selector": getattr(item, "check_selector", None),
        "property_name": getattr(item, "property_name", None),
        "operator": _value(getattr(item, "operator", None), "equals"),
        "expected_value": getattr(item, "expected_value", None),
        "wait_ms": getattr(item, "wait_ms", 0),
        "points": getattr(item, "points", 0),
        "group_id": getattr(item, "group_id", None),
        "sequence_order": getattr(item, "sequence_order", None),
        "execution_mode": _value(getattr(item, "execution_mode", None), "isolated"),
    }


def _run_sync_evaluation(html: str, css: str, js: str, assertions: list[dict], capture_only: bool) -> list[dict]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = browser.new_context(
            java_script_enabled=True,
            offline=True,
            viewport={"width": 1280, "height": 720},
            locale="en-US",
            timezone_id="UTC",
            device_scale_factor=1,
            service_workers="block",
        )
        context.set_default_timeout(3000)
        context.route("**/*", lambda route: route.abort())
        context.add_init_script(
            f"""
            (() => {{
              let seed = 123456789;
              Math.random = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
            }})();
            """
        )
        page = context.new_page()

        evaluator = CandidateEvaluator(page)
        typed = [
            Assertion(
                id=str(item.get("id") or f"temp-{index}"),
                trigger=TriggerType(item.get("trigger", "page_load")),
                trigger_selector=item.get("trigger_selector"),
                input_value=item.get("input_value"),
                check_type=CheckType(item.get("check_type", "dom_presence")),
                check_selector=item.get("check_selector"),
                property_name=item.get("property_name"),
                operator=Operator(item.get("operator", "equals")),
                expected_value=item.get("expected_value"),
                wait_ms=int(item.get("wait_ms") or 0),
                points=int(item.get("points") or 0),
                group_id=item.get("group_id"),
                sequence_order=item.get("sequence_order"),
                execution_mode=item.get("execution_mode", "isolated"),
            )
            for index, item in enumerate(assertions)
        ]
        try:
            result = evaluator.evaluate_submission(html, css, js, typed, capture_only=capture_only)
            return [
                {
                    "assertion_id": item.assertion_id,
                    "status": item.status.lower(),
                    "passed": item.status == "PASS",
                    "actual_value": item.actual,
                    "expected_value": item.expected,
                    "error": item.message if item.status != "PASS" else "",
                    "reason": item.reason,
                    "blocked_by": item.blocked_by,
                    "points_awarded": item.points_awarded,
                }
                for item in result.assertion_results
            ]
        finally:
            context.close()
            browser.close()


def _process_entry(queue, html: str, css: str, js: str, assertions: list[dict], capture_only: bool) -> None:
    try:
        queue.put((True, _run_sync_evaluation(html, css, js, assertions, capture_only)))
    except BaseException as exc:
        queue.put((False, f"{type(exc).__name__}: {exc}"))


def _run_with_hard_timeout(html: str, css: str, js: str, assertions: list[dict], capture_only: bool) -> list[dict]:
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    
    # Scale timeout based on number of assertions (min 30s)
    dynamic_timeout = max(30, len(assertions) * 2)

    process = ctx.Process(target=_process_entry, args=(queue, html, css, js, assertions, capture_only), daemon=True)
    process.start()
    process.join(dynamic_timeout)
    if process.is_alive():
        process.terminate()
        process.join(3)
        if process.is_alive() and hasattr(process, "kill"):
            process.kill()
            
        queue.cancel_join_thread()
        raise RuntimeError(f"Playwright evaluation exceeded {dynamic_timeout} seconds.")
    try:
        ok, payload = queue.get(timeout=1)
    except Empty as exc:
        raise RuntimeError(f"Playwright worker exited with code {process.exitcode}") from exc
    finally:
        queue.cancel_join_thread()
        queue.close()
    if not ok:
        raise RuntimeError(payload)
    return payload


async def evaluate_submission(
    html: str,
    css: str,
    js: str,
    assertions: list,
    *,
    capture_only: bool = False,
) -> list[dict]:
    serialized = [serialize_assertion(item) for item in assertions]
    return await asyncio.to_thread(_run_with_hard_timeout, html, css, js, serialized, capture_only)
