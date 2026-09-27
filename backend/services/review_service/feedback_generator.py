from config import settings
from ai.llm_client.client import client  # shared Mistral client instance
from ai.llm_client.retry import with_retry
from pydantic import BaseModel
class FeedbackResponse(BaseModel):
    feedback: str


PROMPT = """
You are a friendly QA reviewer writing a brief evaluation summary for a candidate's HTML/CSS/JS submission.

You will receive:
- Test Case results (Playwright pass/fail per assertion)
- The AI Grade Assessment: a score out of 50 across 5 quality dimensions, with reasoning, strengths, and areas for improvement already determined

Write 2-3 sentences in plain English that are CONSISTENT with both the test case results AND the AI Grade Assessment:
- If test cases passed but the AI Grade is low, say so plainly — e.g. "The core functionality works, but the code quality assessment flagged issues with X and Y."
- Do not describe the submission as fully successful if the AI Grade Assessment is 25 or lower (Insufficient/Failed).
- Reference the actual dimension(s) that scored lowest, using the improvements provided.

IMPORTANT: You are NOT re-judging any result. All pass/fail decisions and scores are already made. You are only explaining the already-computed outcome, and your summary must not contradict the verdict.
"""

async def generate_eval_feedback(html: str, css: str, js: str, eval_results: list, llm_grade: dict = None) -> str:
    # Format the results for the LLM
    results_text = "\n".join([
        f"- Check: {r['expected']} | Actual: {r['actual']} | Passed: {r['passed']}"
        for r in eval_results
    ])
    
    import json
    grade_text = json.dumps(llm_grade, indent=2) if llm_grade else "No AI grade available."

    try:
        from ai.llm_client.client import call_llm_structured
        result = await call_llm_structured(
            system_prompt=PROMPT,
            user_message=f"""Candidate HTML:
{html}

CSS:
{css}

JS:
{js}

Results:
{results_text}

AI Grade Assessment:
{grade_text}""",
            schema=FeedbackResponse,
            model=settings.llm_model_scoring,
            thinking_level="minimal"
        )

        content = result.get("feedback")
        if not content or not content.strip():
            return "Evaluation complete. Feedback generation was skipped."
        return content.strip()
    except Exception as e:
        print(f"Feedback generation failed: {e}")
        return "Evaluation complete. AI feedback is currently unavailable."
