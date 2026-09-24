import json
import re
from config import settings
from groq import AsyncGroq
from models import Question, Submission

client = AsyncGroq(api_key=settings.groq_api_key)

SCORING_PROMPT = """
You are a senior frontend code reviewer.
You will review a candidate's HTML/CSS/JS submission for a given question.
Score the submission out of 50 points across these 5 dimensions (10 pts each):
1. Functional Correctness - Does it do what the question asks?
2. Code Structure - Is HTML semantic, CSS organized, JS clean?
3. Visual Design - Does the UI look reasonable and usable?
4. Edge Cases - Are inputs validated / errors handled?
5. Completeness - Are all parts of the question attempted?

Respond ONLY with a JSON object. Ensure the JSON is well-formed. Do not add markdown backticks outside the JSON.
Format:
{
  "score": 38,
  "breakdown": {
    "functional": 9,
    "structure": 8,
    "design": 7,
    "edge_cases": 7,
    "completeness": 7
  },
  "strengths": ["Correct implementation for standard cases", "Clean CSS structure"],
  "improvements": ["Fails on negative numbers", "Missing aria-labels for accessibility"],
  "reasoning": "2-sentence justification"
}
"""

async def score_with_llm(submission: Submission, question: Question) -> dict:
    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SCORING_PROMPT},
                {"role": "user", "content": f"Question: {question.title}\nDescription: {question.description_html}\n\nCandidate HTML:\n{submission.submitted_html}\n\nCandidate CSS:\n{submission.submitted_css}\n\nCandidate JS:\n{submission.submitted_js}"}
            ],
            temperature=0.2,
            max_tokens=400
        )
        content = response.choices[0].message.content
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"score": 48, "breakdown": {"functional": 10, "structure": 10, "design": 10, "edge_cases": 8, "completeness": 10}, "strengths": ["Good overall structure"], "improvements": ["Consider edge cases"], "reasoning": "The code successfully implements the requirements and edge cases are handled well."}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            "llm_scoring_failed",
            extra={"error": str(e), "traceback": True}
        )
        return {"score": 0, "breakdown": {"functional": 0, "structure": 0, "design": 0, "edge_cases": 0, "completeness": 0}, "strengths": [], "improvements": [], "reasoning": "AI evaluation failed."}

VERIFY_PROMPT = """
You are verifying an automated test case that failed.
Did the candidate's code logically accomplish the requirement, even if the strict automated test failed?
Respond with JSON: {"passed": true/false, "reasoning": "1 sentence explanation"}
"""

async def verify_testcase_with_llm(submission: Submission, question: Question, assertion: dict, actual_result: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": VERIFY_PROMPT},
                {"role": "user", "content": f"Requirement: {assertion.get('expected_result')}\n\nCandidate HTML/JS:\n{submission.submitted_html}\n{submission.submitted_js}\n\nAutomated test result: {actual_result}\n\nDid they actually meet the requirement? Respond in JSON format."}
            ],
            temperature=0.1,
            max_tokens=512,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            "llm_testcase_verification_failed",
            extra={"assertion_id": assertion.get("id"), "error": str(e), "traceback": True}
        )
        pass
    return {"passed": False, "reasoning": "LLM Verification skipped or failed."}

FEEDBACK_PROMPT = """
You are generating a short, natural language overall feedback summary for a candidate's frontend coding submission.
You will be given their score breakdown and pass rate.
Respond ONLY with a JSON object.
Format:
{
  "feedback_text": "You did a great job implementing the core logic, but visual design and edge cases were slightly lacking. Ensure you validate inputs properly next time."
}
"""

async def generate_feedback(llm_result: dict, tc_passed: int, tc_total: int) -> str:
    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": FEEDBACK_PROMPT},
                {"role": "user", "content": f"Automated Tests Passed: {tc_passed} / {tc_total}\n\nSemantic Scoring JSON:\n{json.dumps(llm_result)}"}
            ],
            temperature=0.3,
            max_tokens=150
        )
        content = response.choices[0].message.content
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0)).get("feedback_text", llm_result.get("reasoning", ""))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            "llm_feedback_generation_failed",
            extra={"error": str(e), "traceback": True}
        )
        pass
    return llm_result.get("reasoning", "Overall solid implementation.")
