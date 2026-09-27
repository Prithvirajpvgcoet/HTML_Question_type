import json
import logging
from datetime import datetime
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Submission, Assertion, EvaluationResult, TCStatus, SubmissionStatus, Question
from models.evaluation_result import LLMStatus

from services.evaluation_service.runner import evaluate_submission
from services.scoring_service.llm_scorer import score_with_llm, verify_testcases_batch_with_llm

logger = logging.getLogger(__name__)


async def _fire_webhook(submission: Submission):
    """Fire evaluation complete webhook. Silently logs failures."""
    try:
        import httpx
        webhook_url = "http://localhost:8000/api/v1/webhook_stub"  # TODO: move to settings
        payload = {
            "event": "evaluation.completed",
            "submission_id": submission.id,
            "candidate_name": submission.candidate_name,
            "total_score": submission.total_score,
            "status": "completed"
        }
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=2.0)
    except Exception as e:
        logger.warning(f"Webhook fire failed for submission {submission.id}: {e}")


async def process_evaluation_task(submission_id: str):
    async with AsyncSessionLocal() as db:
        # 1. Fetch submission
        sub_res = await db.execute(select(Submission).where(Submission.id == submission_id))
        submission = sub_res.scalar_one_or_none()
        if not submission:
            return

        # 2. Fetch assertions and question
        assert_res = await db.execute(
            select(Assertion).where(Assertion.question_id == submission.question_id)
        )
        assertions = assert_res.scalars().all()

        q_res = await db.execute(select(Question).where(Question.id == submission.question_id))
        question = q_res.scalar_one_or_none()

        # If no assertions at all, mark as completed with 0 score
        if not assertions:
            submission.status = SubmissionStatus.completed
            submission.total_score = 0
            submission.tc_passed = 0
            submission.tc_total = 0
            submission.max_score = 100
            submission.evaluated_at = datetime.utcnow()
            await db.commit()
            await _fire_webhook(submission)
            return

        # 3. Mark as evaluating
        submission.status = SubmissionStatus.evaluating
        await db.commit()

        try:
            # 4. Run Playwright tests
            results = await evaluate_submission(
                html=submission.submitted_html or "",
                css=submission.submitted_css or "",
                js=submission.submitted_js or "",
                assertions=assertions
            )

            # 5. Save evaluation results and tally tc_score
            tc_points_earned = 0
            tc_passed_count = 0

            # Map assertions for quick lookup
            assertion_map = {a.id: a for a in assertions}
            # Collect failed cases for batch processing
            failed_cases = []
            for r in results:
                if not r["passed"] and question:
                    a_model = assertion_map.get(r["assertion_id"])
                    if a_model:
                        failed_cases.append({
                            "assertion_id": r["assertion_id"],
                            "expected_result": a_model.expected_result,
                            "actual_result": r["actual_value"]
                        })
            
            # Batch verify failed cases
            batch_results = await verify_testcases_batch_with_llm(submission, question, failed_cases)

            for r in results:
                a_model = assertion_map.get(r["assertion_id"])
                eval_record = EvaluationResult(
                    submission_id=submission.id,
                    assertion_id=r["assertion_id"],
                    assertion_set_version=a_model.assertion_set_version if a_model else 1,
                    tc_status=TCStatus.passed if r["passed"] else TCStatus.failed,
                    actual_result=r["actual_value"],
                    points_awarded=r["points_awarded"]
                )
                
                if r["passed"]:
                    # BUG-5: Playwright passed cleanly - skip LLM, set explicit status
                    eval_record.llm_status = LLMStatus.skipped_playwright_passed
                    eval_record.llm_evidence_text = "Playwright check passed; LLM verification not needed."
                elif question and r["assertion_id"] in batch_results:
                    a_model = assertion_map.get(r["assertion_id"])
                    verify_res = batch_results[r["assertion_id"]]
                    
                    if verify_res.get("passed"):
                        eval_record.llm_status = LLMStatus.verified_pass
                        # Overwrite Playwright failure if LLM validates semantic intent
                        eval_record.tc_status = TCStatus.passed
                        r["passed"] = True
                        r["points_awarded"] = getattr(a_model, "points", 10) if a_model else 10
                        eval_record.points_awarded = r["points_awarded"]
                    else:
                        eval_record.llm_status = LLMStatus.verified_fail
                    eval_record.llm_evidence_text = verify_res.get("reasoning", "")
                elif not question:
                    pass
                
                tc_points_earned += r["points_awarded"]
                if r["passed"]:
                    tc_passed_count += 1
                db.add(eval_record)

            tc_total_points = sum(a.points for a in assertions)

            # 6. Run LLM Semantic Scoring (the remaining 50%)
            
            from models.submission import SubmissionLLMStatus
            
            # 6. Run LLM Semantic Scoring (the remaining 50%)
            # Gate: only skip if EVERY single Playwright test failed (nothing to score).
            # Partial passes still deserve AI feedback and a real LLM score.
            llm_score = 0
            if question:
                if tc_passed_count == 0 and len(assertions) > 0:
                    # All tests failed — no point running LLM on a blank slate
                    submission.llm_status = SubmissionLLMStatus.skipped_due_to_failure
                    submission.ai_feedback_breakdown = "{}"
                    submission.ai_feedback_text = (
                        "AI Semantic Scoring was skipped because all automated test cases failed. "
                        "Please review the test case results above."
                    )
                    submission.ai_confidence = "low"
                else:
                    submission.llm_status = SubmissionLLMStatus.evaluated
                    llm_result = await score_with_llm(submission, question, tc_passed_count, len(assertions))
                    # Clamp score between 0 and 50
                    llm_score = min(max(int(llm_result.get("score", 0)), 0), 50)

                    # Merge strengths and improvements into the breakdown JSON for the frontend
                    breakdown_data = llm_result.get("breakdown", {})
                    breakdown_data["strengths"] = llm_result.get("strengths", [])
                    breakdown_data["improvements"] = llm_result.get("improvements", [])
                    submission.ai_feedback_breakdown = json.dumps(breakdown_data)

                    eval_feedback_list = []
                    for r in results:
                        a_model = assertion_map.get(r["assertion_id"])
                        eval_feedback_list.append({
                            "expected": a_model.expected_result if a_model else "unknown",
                            "actual": r["actual_value"],
                            "passed": r["passed"]
                        })

                    try:
                        from services.review_service.feedback_generator import generate_eval_feedback
                        feedback_text = await generate_eval_feedback(
                            html=submission.submitted_html or "",
                            css=submission.submitted_css or "",
                            js=submission.submitted_js or "",
                            eval_results=eval_feedback_list,
                            llm_grade=llm_result
                        )
                        submission.ai_feedback_text = feedback_text
                    except Exception as e:
                        logger.error(f"Feedback generation failed for submission {submission_id}: {e}")
                        submission.ai_feedback_text = "Evaluation complete. Detailed feedback generation failed."

                    submission.ai_confidence = "high" if llm_score >= 35 else "medium" if llm_score >= 20 else "low"

            submission.tc_passed = tc_passed_count
            submission.tc_total = len(assertions)
            submission.llm_passed = llm_score
            submission.llm_total = 50
            submission.total_score = tc_points_earned + llm_score
            submission.max_score = tc_total_points + 50
            submission.status = SubmissionStatus.completed
            submission.evaluated_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Evaluation failed for submission {submission_id}: {e}")
            submission.status = SubmissionStatus.failed
            submission.ai_feedback_text = f"Evaluation crashed: {str(e)}"

        finally:
            await db.commit()

        await _fire_webhook(submission)
