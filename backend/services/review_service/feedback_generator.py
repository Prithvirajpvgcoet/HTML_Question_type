import json

from pydantic import BaseModel

from config import settings


class FeedbackResponse(BaseModel):
    feedback: str


PROMPT = """
You write a brief recruiter-facing summary for an HTML/CSS/JS coding submission.

You will receive:
- The deterministic Playwright score
- Assertion-level Playwright results with expected values, actual browser values, and status

Write 2-3 sentences in plain English. You are not grading, scoring, re-judging, or changing pass/fail outcomes. Do not mention code quality unless it is directly represented by a Playwright assertion. Do not contradict the supplied score or assertion statuses.
"""


async def generate_eval_feedback(score: int, max_score: int, eval_results: list[dict]) -> str:
    try:
        from ai.llm_client.client import call_llm_structured

        result = await call_llm_structured(
            system_prompt=PROMPT,
            user_message=json.dumps(
                {
                    "score": score,
                    "max_score": max_score,
                    "assertion_results": eval_results,
                },
                indent=2,
            ),
            schema=FeedbackResponse,
            model=settings.llm_model_scoring,
            thinking_level="minimal",
        )
        return (result.get("feedback") or "").strip()
    except Exception:
        return ""
