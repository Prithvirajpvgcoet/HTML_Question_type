import asyncio
import json
import threading
from pathlib import Path

import pytest
from types import SimpleNamespace

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

from services.evaluation_service.evaluator import (
    Assertion,
    CandidateEvaluator,
    CheckType,
    Operator,
    TriggerType,
)
from services.evaluation_service.runner import _run_sync_evaluation


GOLDEN_SET_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "golden_set.json"


def _load_golden_set() -> dict:
    return json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))


def _golden_assertions() -> list[Assertion]:
    assertions = []
    for item in _load_golden_set()["assertions"]:
        assertions.append(
            Assertion(
                id=item["id"],
                trigger=TriggerType(item["trigger"]),
                check_type=CheckType(item["check_type"]),
                trigger_selector=item.get("trigger_selector"),
                check_selector=item.get("check_selector"),
                property_name=item.get("property_name"),
                operator=Operator(item.get("operator", "equals")),
                expected_value=item.get("expected_value"),
                input_value=item.get("input_value"),
                points=item.get("points", 0),
                group_id=item.get("group_id"),
                sequence_order=item.get("sequence_order"),
                execution_mode=item.get("execution_mode", "isolated"),
                wait_ms=item.get("wait_ms", 0),
            )
        )
    return assertions


GOLDEN_SET = _load_golden_set()
GOOD_SUBMISSIONS = GOLDEN_SET["good_submissions"]
BROKEN_SUBMISSIONS = GOLDEN_SET["broken_submissions"]


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720}, locale="en-US", timezone_id="UTC")
        yield context.new_page()
        browser.close()


def test_supported_checks_and_exact_equals(page):
    evaluator = CandidateEvaluator(page)
    assertions = [
        Assertion("presence", TriggerType.PAGE_LOAD, CheckType.DOM_PRESENCE, check_selector="#count", operator=Operator.EXISTS, points=10),
        Assertion("absence", TriggerType.PAGE_LOAD, CheckType.DOM_ABSENCE, check_selector="#missing", operator=Operator.NOT_EXISTS, points=10),
        Assertion("count", TriggerType.PAGE_LOAD, CheckType.ELEMENT_COUNT, check_selector=".item", expected_value="2", points=10),
        Assertion("text", TriggerType.PAGE_LOAD, CheckType.TEXT_CONTENT, check_selector="#count", expected_value="1", points=10),
        Assertion("attr", TriggerType.PAGE_LOAD, CheckType.ATTRIBUTE, check_selector="#field", property_name="type", expected_value="password", points=10),
        Assertion("style", TriggerType.PAGE_LOAD, CheckType.COMPUTED_STYLE, check_selector="#count", property_name="color", expected_value="rgb(255, 0, 0)", points=10),
    ]
    result = evaluator.evaluate_submission(
        '<span class="item"></span><span class="item"></span><strong id="count">1</strong><input id="field" type="password">',
        "#count { color: red; }", "", assertions,
    )
    assert result.total_points == 60

    assertions[3].expected_value = "10"
    result = evaluator.evaluate_submission('<strong id="count">1</strong>', "", "", [assertions[3]])
    assert result.total_points == 0


def test_sequential_failure_blocks_later_steps(page):
    evaluator = CandidateEvaluator(page)
    assertions = [
        Assertion("1", TriggerType.CLICK, CheckType.TEXT_CONTENT, "#missing", "#count", expected_value="1", points=10,
                  group_id="counter", sequence_order=1, execution_mode="sequential"),
        Assertion("2", TriggerType.CLICK, CheckType.TEXT_CONTENT, "#increment", "#count", expected_value="2", points=10,
                  group_id="counter", sequence_order=2, execution_mode="sequential"),
    ]
    result = evaluator.evaluate_submission('<button id="increment"></button><span id="count">0</span>', "", "", assertions)
    assert result.assertion_results[0].status == "FAIL"
    assert result.assertion_results[1].status == "SKIPPED"
    assert result.assertion_results[1].blocked_by == "1"


def test_call_function_and_function_presence(page):
    evaluator = CandidateEvaluator(page)
    js = "function setProgress(value) { document.querySelector('#progress').textContent = value + '%'; }"
    assertions = [
        Assertion("fn", TriggerType.PAGE_LOAD, CheckType.FUNCTION_PRESENCE, check_selector="setProgress",
                  operator=Operator.EXISTS, points=10),
        Assertion("call", TriggerType.CALL_FUNCTION, CheckType.TEXT_CONTENT, trigger_selector="setProgress",
                  input_value="[50]", check_selector="#progress", expected_value="50%", points=10),
    ]
    result = evaluator.evaluate_submission('<div id="progress">0%</div>', "", js, assertions)
    assert [item.status for item in result.assertion_results] == ["PASS", "PASS"]


def test_capture_mode_returns_browser_value_without_scoring(page):
    evaluator = CandidateEvaluator(page)
    assertion = Assertion("capture", TriggerType.PAGE_LOAD, CheckType.TEXT_CONTENT, check_selector="#value", points=10)
    result = evaluator.evaluate_submission('<div id="value">browser canonical value</div>', "", "", [assertion], capture_only=True)
    assert result.total_points == 0
    assert result.assertion_results[0].actual == "browser canonical value"


def test_process_runner_returns_assertion_evidence():
    from services.evaluation_service.runner import _run_with_hard_timeout

    results = _run_with_hard_timeout(
        '<div id="value">1</div>', "", "",
        [{
            "id": "exact", "trigger": "page_load", "check_type": "text_content",
            "check_selector": "#value", "operator": "equals", "expected_value": "1",
            "points": 10, "execution_mode": "isolated",
        }],
        False,
    )
    assert results[0] == {
        "assertion_id": "exact", "status": "pass", "passed": True,
        "actual_value": "1", "expected_value": "1", "error": "",
        "reason": None, "blocked_by": None, "points_awarded": 10,
    }


def test_runner_does_not_disable_web_security(monkeypatch):
    launch_args = {}

    class FakeBrowser:
        def new_context(self, **kwargs):
            raise RuntimeError("stop after launch")

        def close(self):
            pass

    class FakeChromium:
        def launch(self, **kwargs):
            launch_args.update(kwargs)
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr("services.evaluation_service.runner.sync_playwright", lambda: FakePlaywright())
    with pytest.raises(RuntimeError, match="stop after launch"):
        _run_sync_evaluation("", "", "", [], False)
    assert "--disable-web-security" not in launch_args["args"]


def test_reference_validation_rejects_assertions_that_empty_submission_can_score(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.v1.questions import crud

    async def fake_evaluate_submission(html, css, js, assertions, capture_only=False):
        if capture_only:
            return [
                {"assertion_id": "presence", "passed": True, "actual_value": "Ready"},
                {"assertion_id": "absence", "passed": True, "actual_value": True},
            ]
        return [
            {"assertion_id": "presence", "points_awarded": 0},
            {"assertion_id": "absence", "points_awarded": 50},
        ]

    class FakeDb:
        async def commit(self):
            pass

        async def refresh(self, _):
            pass

    q = SimpleNamespace(id="question-1", reference_html="<div id='status'>Ready</div>", reference_css="", reference_js="")
    assertions = [
        SimpleNamespace(id="presence", operator="equals", expected_value=None, points=50),
        SimpleNamespace(id="absence", operator="not_exists", expected_value=None, points=50),
    ]
    monkeypatch.setattr(crud, "evaluate_submission", fake_evaluate_submission)

    outcome = {}

    def run_validation():
        try:
            outcome["value"] = asyncio.run(crud._validate_against_reference(q, assertions, FakeDb()))
        except BaseException as exc:
            outcome["error"] = exc

    thread = threading.Thread(target=run_validation)
    thread.start()
    thread.join()
    if "error" in outcome:
        raise outcome["error"]
    split = outcome["value"]

    assert len(split["failed"]) == 2
    assert {item.id for item in split["failed"]} == {"presence", "absence"}
    assert all("empty submission scored 50.0%" in item.last_validation_error for item in split["failed"])


def test_golden_set_fixture_shape():
    assert GOLDEN_SET_PATH.exists()
    assert len(GOOD_SUBMISSIONS) == 10
    assert len(BROKEN_SUBMISSIONS) == 3
    assert sum(item["points"] for item in GOLDEN_SET["assertions"]) == 100
    assert {item["name"] for item in GOOD_SUBMISSIONS}.isdisjoint(
        {item["name"] for item in BROKEN_SUBMISSIONS}
    )


@pytest.mark.parametrize("submission", GOOD_SUBMISSIONS, ids=[item["name"] for item in GOOD_SUBMISSIONS])
def test_golden_set_good_submissions(page, submission):
    evaluator = CandidateEvaluator(page)
    result = evaluator.evaluate_submission(
        submission["html"],
        submission["css"],
        submission["js"],
        _golden_assertions(),
    )
    assert result.total_points == 100, submission["name"]


@pytest.mark.parametrize("submission", BROKEN_SUBMISSIONS, ids=[item["name"] for item in BROKEN_SUBMISSIONS])
def test_golden_set_broken_submissions(page, submission):
    evaluator = CandidateEvaluator(page)
    result = evaluator.evaluate_submission(
        submission["html"],
        submission["css"],
        submission["js"],
        _golden_assertions(),
    )
    assert result.total_points < 100, submission["name"]
