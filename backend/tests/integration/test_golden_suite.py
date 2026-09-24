import pytest
from playwright.sync_api import sync_playwright
from services.evaluation_service.evaluator import CandidateEvaluator, Assertion, TriggerType, CheckType

# ---------------------------------------------------------
# Golden Suite Data
# ---------------------------------------------------------

GOLDEN_ASSERTIONS = [
    # 1. Color matching (Semantic)
    Assertion(
        id="a1", trigger=TriggerType.PAGE_LOAD, check_type=CheckType.COMPUTED_STYLE,
        trigger_selector=None, check_selector="#color-box",
        property_name="background-color", expected_value="red", points=10
    ),
    # 2. Boolean Attribute Logic (Disabled button)
    Assertion(
        id="a2", trigger=TriggerType.PAGE_LOAD, check_type=CheckType.ATTRIBUTE,
        trigger_selector=None, check_selector="#submit-btn",
        property_name="disabled", expected_value="true", points=10
    ),
    # 3. Sequencing / State (Fill input to enable button, then hover)
    Assertion(
        id="a3", trigger=TriggerType.INPUT, check_type=CheckType.ATTRIBUTE,
        trigger_selector="#username", check_selector="#submit-btn", input_value="testuser",
        property_name="disabled", expected_value="false", points=10,
        group_id="flow_1", sequence_order=1
    ),
    Assertion(
        id="a4", trigger=TriggerType.HOVER, check_type=CheckType.COMPUTED_STYLE,
        trigger_selector="#submit-btn", check_selector="#submit-btn",
        property_name="cursor", expected_value="pointer", points=10,
        group_id="flow_1", sequence_order=2
    ),
]

PASS_HTML = """
<div id="color-box"></div>
<input type="text" id="username" />
<button id="submit-btn" disabled>Submit</button>
"""

PASS_CSS = """
#color-box { background-color: rgb(255, 0, 0); }
#submit-btn:not([disabled]):hover { cursor: pointer; }
"""

PASS_JS = """
document.getElementById("username").addEventListener("input", (e) => {
    if(e.target.value.length > 0) document.getElementById("submit-btn").disabled = false;
    else document.getElementById("submit-btn").disabled = true;
});
"""

FAIL_HTML = """
<div id="color-box"></div>
<input type="text" id="username" />
<button id="submit-btn">Submit</button> <!-- Bug: Not disabled initially -->
"""

FAIL_CSS = """
#color-box { background-color: rgb(0, 0, 255); } /* Bug: Wrong color */
"""

FAIL_JS = """
// Bug: No logic to enable button or pointer cursor
"""

# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------

@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        yield page
        browser.close()

def test_golden_pass(browser_context):
    evaluator = CandidateEvaluator(browser_context)
    result = evaluator.evaluate_submission(PASS_HTML, PASS_CSS, PASS_JS, GOLDEN_ASSERTIONS)
    
    assert result.total_points == 40
    for res in result.assertion_results:
        assert res.status == "PASS", f"Assertion {res.assertion_id} failed unexpectedly: {res.message}"

def test_golden_fail(browser_context):
    evaluator = CandidateEvaluator(browser_context)
    result = evaluator.evaluate_submission(FAIL_HTML, FAIL_CSS, FAIL_JS, GOLDEN_ASSERTIONS)
    
    # Expecting failure on:
    # a1: background-color is blue, expected red -> FAIL
    # a2: button is not disabled -> FAIL
    # a3: input triggers nothing, button stays enabled, technically expected_value="false" so actual is "false", wait, if it's already enabled, it might pass? Let's assume some fail.
    
    assert result.total_points < 40
    
    a1_res = next(r for r in result.assertion_results if r.assertion_id == "a1")
    assert a1_res.status == "FAIL"
    
    a2_res = next(r for r in result.assertion_results if r.assertion_id == "a2")
    assert a2_res.status == "FAIL"



from services.evaluation_service.runner import parse_expected_result

@pytest.mark.parametrize("check_type,expected_result,want_prop,want_value", [
    ("attribute", "type: password", "type", "password"),
    ("attribute", "value: testuser", "value", "testuser"),
    ("attribute", "value=secret", "value", "secret"),
    ("text_content", "text: Log in", None, "Log in"),
    ("text_content", "content: Welcome", None, "Welcome"),
    ("computed_style", "background-color: red", "background-color", "red"),
    ("dom_presence", "element should exist", None, "element should exist")
])
def test_parse_expected_result(check_type, expected_result, want_prop, want_value):
    assert parse_expected_result(check_type, expected_result) == (want_prop, want_value)
def test_reference_gate_catches_missing_precondition(browser_context):
    from services.evaluation_service.evaluator import CandidateEvaluator, Assertion, TriggerType, CheckType
    ref_html = """
        <input id='username' /><input id='password' type='password' />
        <button id='loginBtn' disabled>Login</button>
    """
    ref_js = """
        function check() {
            document.getElementById('loginBtn').disabled =
                !(document.getElementById('username').value &&
                  document.getElementById('password').value);
        }
        document.getElementById('username').addEventListener('input', check);
        document.getElementById('password').addEventListener('input', check);
    """
    incomplete_assertions = [
        Assertion(
            id='x1', trigger=TriggerType.INPUT, check_type=CheckType.ATTRIBUTE,
            trigger_selector='#username', check_selector='#loginBtn',
            input_value='alice', property_name='disabled', expected_value='false',
            points=10, group_id='g1', sequence_order=1
        ),
    ]
    evaluator = CandidateEvaluator(browser_context)
    result = evaluator.evaluate_submission(ref_html, '', ref_js, incomplete_assertions)
    assert result.total_points == 0, 'Reference solution must fail an incomplete precondition assertion.'

def test_multifield_precondition_correct_set_passes(browser_context):
    from services.evaluation_service.evaluator import CandidateEvaluator, Assertion, TriggerType, CheckType
    ref_html = """
        <input id='username' /><input id='password' type='password' />
        <button id='loginBtn' disabled>Login</button>
    """
    ref_js = """
        function check() {
            document.getElementById('loginBtn').disabled =
                !(document.getElementById('username').value &&
                  document.getElementById('password').value);
        }
        document.getElementById('username').addEventListener('input', check);
        document.getElementById('password').addEventListener('input', check);
    """
    complete_assertions = [
        Assertion(
            id='c1', trigger=TriggerType.INPUT, check_type=CheckType.DOM_PRESENCE,
            trigger_selector='#username', check_selector='#username',
            input_value='alice', expected_value='true', points=5,
            group_id='g1', sequence_order=1
        ),
        Assertion(
            id='c2', trigger=TriggerType.INPUT, check_type=CheckType.ATTRIBUTE,
            trigger_selector='#password', check_selector='#loginBtn',
            input_value='secret', property_name='disabled', expected_value='false',
            points=10, group_id='g1', sequence_order=2
        ),
    ]
    evaluator = CandidateEvaluator(browser_context)
    result = evaluator.evaluate_submission(ref_html, '', ref_js, complete_assertions)
    assert result.total_points == 15

def test_execution_mode_isolation(browser_context):
    html = '''
        <button id="toggleBtn">Off</button>
    '''
    js = '''
        const btn = document.getElementById('toggleBtn');
        btn.addEventListener('click', () => {
            btn.textContent = btn.textContent === 'Off' ? 'On' : 'Off';
        });
    '''
    
    # We want three assertions:
    # 1. Click toggle, check text is 'On' (sequential, group 'g1', order 1)
    # 2. Page load, check text is 'Off' (isolated) - shouldn't see the click from 1
    # 3. Click toggle, check text is 'Off' (sequential, group 'g1', order 2) - should see the click from 1
    
    assertions = [
        Assertion(
            id='a1', trigger=TriggerType.CLICK, trigger_selector='#toggleBtn',
            check_type=CheckType.TEXT_CONTENT, check_selector='#toggleBtn',
            expected_value='On', points=10, group_id='g1', sequence_order=1, execution_mode='sequential'
        ),
        Assertion(
            id='a2', trigger=TriggerType.PAGE_LOAD, trigger_selector='',
            check_type=CheckType.TEXT_CONTENT, check_selector='#toggleBtn',
            expected_value='Off', points=10, group_id=None, sequence_order=None, execution_mode='isolated'
        ),
        Assertion(
            id='a3', trigger=TriggerType.CLICK, trigger_selector='#toggleBtn',
            check_type=CheckType.TEXT_CONTENT, check_selector='#toggleBtn',
            expected_value='Off', points=10, group_id='g1', sequence_order=2, execution_mode='sequential'
        )
    ]
    
    evaluator = CandidateEvaluator(browser_context)
    result = evaluator.evaluate_submission(html, '', js, assertions)
    assert result.total_points == 30
def test_dom_presence_expectation(browser_context):
    html = '''
        <div id="exists">I exist</div>
    '''
    js = ''
    
    assertions = [
        # Expected Present, Element Exists -> PASS
        Assertion(
            id='a1', trigger=TriggerType.PAGE_LOAD, check_type=CheckType.DOM_PRESENCE,
            trigger_selector='', check_selector='#exists',
            expected_value='present', points=10, group_id='g1', execution_mode='isolated'
        ),
        # Expected Present, Element Missing -> FAIL
        Assertion(
            id='a2', trigger=TriggerType.PAGE_LOAD, check_type=CheckType.DOM_PRESENCE,
            trigger_selector='', check_selector='#missing',
            expected_value='present', points=10, group_id='g2', execution_mode='isolated'
        ),
        # Expected Absent, Element Missing -> PASS
        Assertion(
            id='a3', trigger=TriggerType.PAGE_LOAD, check_type=CheckType.DOM_PRESENCE,
            trigger_selector='', check_selector='#missing',
            expected_value='absent', points=10, group_id='g3', execution_mode='isolated'
        ),
        # Expected Absent, Element Exists -> FAIL
        Assertion(
            id='a4', trigger=TriggerType.PAGE_LOAD, check_type=CheckType.DOM_PRESENCE,
            trigger_selector='', check_selector='#exists',
            expected_value='absent', points=10, group_id='g4', execution_mode='isolated'
        )
    ]
    
    evaluator = CandidateEvaluator(browser_context)
    result = evaluator.evaluate_submission(html, '', js, assertions)
    
    # We should have 20 points (10 for a1, 10 for a3)
    assert result.total_points == 20
    
    # Let's also check the exact statuses
    status_map = {ar.assertion_id: ar.status for ar in result.assertion_results}
    assert status_map['a1'] == 'PASS'
    assert status_map['a2'] == 'FAIL'
    assert status_map['a3'] == 'PASS'
    assert status_map['a4'] == 'FAIL'
