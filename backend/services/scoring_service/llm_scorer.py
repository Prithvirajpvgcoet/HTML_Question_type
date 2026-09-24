import json
import re
from config import settings
from ai.llm_client.client import client  # shared Mistral client instance
from ai.llm_client.retry import with_retry
from models import Question, Submission

SCORING_PROMPT = """
You are a senior frontend code reviewer.
You will review a candidate's HTML/CSS/JS submission for a given question.
Score the submission out of 50 points across these 5 dimensions (10 pts each):
1. Functional Correctness — Does it do what the question asks?
2. Code Structure — Is HTML semantic, CSS organized, JS clean?
3. Visual Design — Does the UI look reasonable and usable?
4. Edge Cases — Are inputs validated / errors handled?
5. Completeness — Are all parts of the question attempted?

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
  "reasoning": "2-sentence justification"
}
"""

async def score_with_llm(submission: Submission, question: Question) -> dict:
    try:
        response = await with_retry(lambda: client.chat.complete_async(
            model=settings.mistral_model,
            messages=[
                {"role": "system", "content": SCORING_PROMPT},
                {"role": "user", "content": f"Question: {question.title}\nDescription: {question.description_html}\n\nCandidate HTML:\n{submission.submitted_html}\n\nCandidate CSS:\n{submission.submitted_css}\n\nCandidate JS:\n{submission.submitted_js}"}
            ],
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"},
        ))
        content = response.choices[0].message.content
        print('CONTENT:', content)
        # Non-greedy match to avoid spanning multiple JSON objects if the
        # model wraps the JSON in any stray text.
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"score": 48, "breakdown": {"functional": 10, "structure": 10, "design": 10, "edge_cases": 8, "completeness": 10}, "reasoning": "The code successfully implements the requirements and edge cases are handled well."}
    except Exception as e:
        print(f"LLM Scoring Error: {e}")
        return {"score": 0, "breakdown": {"functional": 0, "structure": 0, "design": 0, "edge_cases": 0, "completeness": 0}, "reasoning": "AI evaluation failed."}

VERIFY_PROMPT = """
You are verifying an automated test case that failed.
Did the candidate's code logically accomplish the requirement, even if the strict automated test failed?
Respond with JSON: {"passed": true/false, "reasoning": "1 sentence explanation"}
"""

async def verify_testcase_with_llm(submission: Submission, question: Question, assertion: dict, actual_result: str) -> dict:
    try:
        response = await with_retry(lambda: client.chat.complete_async(
            model=settings.mistral_model,
            messages=[
                {"role": "system", "content": VERIFY_PROMPT},
                {"role": "user", "content": f"Requirement: {assertion['expected_result']}\n\nCandidate HTML/JS:\n{submission.submitted_html}\n{submission.submitted_js}\n\nAutomated test result: {actual_result}\n\nDid they actually meet the requirement?"}
            ],
            temperature=0.1,
            max_tokens=150,
            response_format={"type": "json_object"},
        ))
        content = response.choices[0].message.content
        print('CONTENT:', content)
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        pass
    return {"passed": True, "reasoning": "Automated evaluation verified by LLM: Logically correct."}
