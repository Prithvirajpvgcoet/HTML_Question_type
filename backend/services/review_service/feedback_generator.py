from config import settings
from ai.llm_client.client import client  # shared Mistral client instance
from ai.llm_client.retry import with_retry
from pydantic import BaseModel
class FeedbackResponse(BaseModel):
    feedback: str


PROMPT = """
You are an expert technical interviewer. You have just automatically graded a candidate's HTML/CSS/JS test.
Given the candidate's code and a list of assertions with their pass/fail status, write a short, constructive 2-3 sentence summary of how they did.
Do not re-evaluate the code. Just summarize the results provided.
"""

async def generate_eval_feedback(html: str, css: str, js: str, eval_results: list) -> str:
    # Format the results for the LLM
    results_text = "\n".join([
        f"- Check: {r['expected']} | Actual: {r['actual']} | Passed: {r['passed']}"
        for r in eval_results
    ])

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
{results_text}""",
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
