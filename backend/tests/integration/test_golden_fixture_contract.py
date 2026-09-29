import json
from pathlib import Path


GOLDEN_SET_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "golden_set.json"


def test_golden_set_fixture_contract():
    golden_set = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    good_submissions = golden_set["good_submissions"]
    broken_submissions = golden_set["broken_submissions"]
    assertions = golden_set["assertions"]

    assert len(good_submissions) == 10
    assert len(broken_submissions) == 3
    assert sum(item["points"] for item in assertions) == 100
    assert {item["name"] for item in good_submissions}.isdisjoint(
        {item["name"] for item in broken_submissions}
    )

    required_submission_fields = {"name", "html", "css", "js"}
    for submission in good_submissions + broken_submissions:
        assert required_submission_fields <= submission.keys()
        assert submission["name"]

    required_assertion_fields = {
        "id",
        "trigger",
        "check_type",
        "check_selector",
        "operator",
        "points",
        "execution_mode",
    }
    for assertion in assertions:
        assert required_assertion_fields <= assertion.keys()
        assert assertion["points"] > 0
