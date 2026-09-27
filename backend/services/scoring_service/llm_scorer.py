import json
import re
from config import settings
from models import Question, Submission
from pydantic import BaseModel, Field
from typing import Literal

class VerifyResult(BaseModel):
    assertion_id: str
    passed: bool
    reasoning: str

class BatchVerifyResult(BaseModel):
    results: list[VerifyResult]

class Breakdown(BaseModel):
    functional: int
    structure: int
    design: int
    edge_cases: int
    completeness: int

class LLMScore(BaseModel):
    score: int
    breakdown: Breakdown
    reasoning: str
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)

SCORING_PROMPT = """
You are a senior frontend code reviewer scoring a candidate's HTML/CSS/JS submission against a SPECIFIC question's requirements — not a generic code review.

You will be given:
- The question's title and description (the exact requirements the candidate had to satisfy)
- The number of automated Playwright test cases that passed/failed (these already verify functional/DOM/style behavior objectively — treat a pass as confirmed evidence, do not re-doubt it)
- The candidate's HTML/CSS/JS

Score out of 50 across these 5 dimensions (10 pts each). For each, judge STRICTLY against what the question actually asked for — do not penalize the candidate for not doing things the question never required:

1. Functional Correctness — Does the submitted code implement exactly what the description asks? If all automated test cases passed, this dimension should score 8-10 unless you find a specific requirement in the description that the tests didn't cover and the code clearly fails.
2. Code Structure — Semantic HTML, organized CSS, clean JS. Only deduct for concrete issues you can name (e.g. "uses <div onclick> instead of <button>", "inline styles instead of a class").
3. Visual Design — Does the UI match what the description implies, using reasonable, usable styling.
4. Edge Cases — Only deduct if the description implies specific edge cases (e.g. empty input, invalid value) that the code visibly does not handle. Do not invent hypothetical edge cases the question never mentioned.
5. Completeness — Every requirement explicitly stated in the description is present in the code.

Rules:
- Every deduction must cite a specific requirement from the description or a specific line/element in the code. Do not write generic phrases like "lacks content" or "needs improvement across all dimensions" without naming what is missing.
- If the candidate's code satisfies the description and passes the test cases, the overall score must reflect that — do not fail a submission that meets its stated requirements.
- Judge code quality (naming, hardcoding, semantics, reuse) as a secondary factor, separate from whether requirements were met — a correct-but-messy solution should score high on Functional Correctness/Completeness even if Code Structure is docked.

Also identify:
- strengths: 1-4 short, specific things the candidate did well (reference actual code/behavior, not generic praise)
- improvements: 1-4 short, specific, actionable gaps tied to a dimension above that scored below 8/10

If a dimension scored 8 or higher, do not invent a criticism for it just to fill the list. It is fine for improvements to be shorter than strengths.
"""

VERIFY_PROMPT = """
You are an AI assistant helping verify an automated UI test result.
Sometimes the automated test (Playwright) fails because the candidate used a slightly different but semantically correct approach.

Your task:
Review the failed test cases. For each, determine if the candidate's code actually satisfies the requirement described.
If the semantic intent is met despite the strict DOM check failing, mark it passed: true.
Otherwise, mark it passed: false.
"""

async def verify_testcases_batch_with_llm(submission: Submission, question: Question, failed_cases: list[dict]) -> dict[str, dict]:
    if not failed_cases:
        return {}

    cases_text = ""
    for idx, fc in enumerate(failed_cases):
        cases_text += f"Case {idx + 1}:\\nAssertion ID: {fc['assertion_id']}\\nRequirement: {fc['expected_result']}\\nAutomated Result: {fc['actual_result']}\\n\\n"

    user_message = f"Candidate HTML/JS:\\n{submission.submitted_html}\\n{submission.submitted_js}\\n\\nEvaluate the following failed cases:\\n\\n{cases_text}"

    try:
        from ai.llm_client.client import call_llm_structured
        response = await call_llm_structured(
            system_prompt=VERIFY_PROMPT,
            user_message=user_message,
            schema=BatchVerifyResult,
            model=settings.llm_model_scoring,
            thinking_level="minimal"
        )
        
        results_map = {}
        for r in response.get("results", []):
            results_map[r["assertion_id"]] = {"passed": r["passed"], "reasoning": r["reasoning"]}
        return results_map
    except Exception as e:
        print(f"Batch verify failed: {e}")
        return {fc['assertion_id']: {"passed": False, "reasoning": "LLM verification unavailable."} for fc in failed_cases}

async def score_with_llm(submission: Submission, question: Question, tc_passed: int, tc_total: int) -> dict:
    user_content = (
        f"Question: {question.title}\n"
        f"Description (requirements): {question.description_html}\n"
        f"Automated test cases: {tc_passed}/{tc_total} passed\n\n"
        f"Candidate HTML:\n{submission.submitted_html}\n\n"
        f"Candidate CSS:\n{submission.submitted_css}\n\n"
        f"Candidate JS:\n{submission.submitted_js}"
    )
    
    try:
        from ai.llm_client.client import call_llm_structured
        result = await call_llm_structured(
            system_prompt=SCORING_PROMPT,
            user_message=user_content,
            schema=LLMScore,
            model=settings.llm_model_scoring,
            thinking_level="minimal"
        )
        return result
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"score_with_llm failed (API error or schema rejection): {e}", exc_info=True)
        return {
            "score": 0,
            "breakdown": {"functional": 0, "structure": 0, "design": 0, "edge_cases": 0, "completeness": 0},
            "reasoning": "Scoring failed due to an AI service error.",
            "strengths": [],
            "improvements": []
        }
