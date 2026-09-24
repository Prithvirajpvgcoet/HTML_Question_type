from config import settings
from groq import AsyncGroq

client = AsyncGroq(api_key=settings.groq_api_key)

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
    
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Candidate HTML:\n{html}\n\nCSS:\n{css}\n\nJS:\n{js}\n\nResults:\n{results_text}"}
        ],
        temperature=0.3,
        max_tokens=150
    )
    
    content = response.choices[0].message.content
    if not content or not content.strip():
        return "Evaluation complete. Feedback generation was skipped."
    return content.strip()
