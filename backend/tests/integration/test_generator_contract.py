import pytest
import asyncio
from services.assertion_service.generator import generate_assertions_from_llm
from services.evaluation_service.runner import parse_expected_result

Q1 = {
    "title": "Login Form",
    "description": "Create a login form. When username and password are provided, enable the submit button. The submit button should have text 'Log in'. Password field should have type password.",
    "html": "<input id='username' /><input id='password' type='password' /><button id='submit' disabled>Log in</button>",
    "css": "",
    "js": ""
}

Q2 = {
    "title": "Hover Card",
    "description": "A card that turns red on hover.",
    "html": "<div id='card'>Hover me</div>",
    "css": "#card:hover { background-color: red; }",
    "js": ""
}

Q3 = {
    "title": "Counter",
    "description": "A counter with a button that increments the text content.",
    "html": "<button id='increment'>0</button>",
    "css": "",
    "js": "document.getElementById('increment').onclick = function() { this.innerText = parseInt(this.innerText) + 1; }"
}

Q4 = {
    "title": "Dynamic Checkbox",
    "description": "A checkbox that when checked, adds a checked attribute.",
    "html": "<input type='checkbox' id='chk' />",
    "css": "",
    "js": ""
}

@pytest.mark.asyncio
@pytest.mark.parametrize("q", [Q1, Q2, Q3, Q4])
async def test_generator_parser_contract(q):
    assertions = await generate_assertions_from_llm(
        title=q["title"],
        description=q["description"],
        html=q["html"],
        css=q["css"],
        js=q["js"]
    )
    
    assert len(assertions) > 0, "Should generate at least some assertions"
    
    for a in assertions:
        check_type = a.get("check_type")
        expected = a.get("expected_result", "")
        
        prop, val = parse_expected_result(check_type, expected)
        
        if check_type in ("computed_style", "attribute"):
            # Should successfully extract a property name
            assert prop is not None, f"Parser failed to extract property from {check_type}: '{expected}'"
        elif check_type == "text_content":
            # For text_content, prop is stripped and None is returned
            # Ensure it didn't just fall back to raw if it had a 'text:' prefix
            if "text:" in expected.lower() or "content:" in expected.lower():
                assert val != expected, f"Parser failed to strip prefix from {check_type}: '{expected}'"
