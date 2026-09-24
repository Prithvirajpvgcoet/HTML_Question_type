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

class LLMScore(BaseModel):
    score: int
    breakdown: dict[str, int]
    reasoning: str
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)

SCORING_PROMPT = \"\"\"
You are a senior frontend code reviewer.
You will review a candidate's HTML/CSS/JS submission for a given question.
Score the submission out of 50 points across these 5 dimensions (10 pts each):
1. Functional Correctness - Does it do what the question asks?
2. Code Structure - Is HTML semantic, CSS organized, JS clean?
3. Visual Design - Does the UI look reasonable and usable?
4. Edge Cases - Are inputs validated / errors handled?
5. Completeness - Are all parts of the question attempted?
\"\"\"

VERIFY_PROMPT = \"\"\"
You are an AI assistant helping verify an automated UI test result.
Sometimes the automated test (Playwright) fails because the candidate used a slightly different but semantically correct approach.

Your task:
Review the failed test cases. For each, determine if the candidate's code actually satisfies the requirement described.
If the semantic intent is met despite the strict DOM check failing, mark it passed: true.
Otherwise, mark it passed: false.
\"\"\"

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

async def score_with_llm(submission: Submission, question: Question) -> dict:
    user_content = f"Question: {question.title}\\n{question.description_html}\\n\\nCandidate Code:\\nHTML:\\n{submission.submitted_html}\\n\\nCSS:\\n{submission.submitted_css}\\n\\nJS:\\n{submission.submitted_js}"
    
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
        print(f"score_with_llm failed: {e}")
        return {
            "score": 0,
            "breakdown": {"functional": 0, "structure": 0, "design": 0, "edge_cases": 0, "completeness": 0},
            "reasoning": "Scoring failed.",
            "strengths": [],
            "improvements": []
        }
