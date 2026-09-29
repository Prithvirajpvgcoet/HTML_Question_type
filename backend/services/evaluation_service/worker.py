import json
import logging
import asyncio
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.future import select

from database import AsyncSessionLocal
from models import Assertion, EvaluationResult, Submission, SubmissionStatus, TCStatus
from services.evaluation_service.runner import evaluate_submission
from services.review_service.feedback_generator import generate_eval_feedback


logger = logging.getLogger(__name__)


async def _fire_webhook(submission: Submission):
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8000/api/v1/webhook_stub",
                json={
                    "event": "evaluation.completed",
                    "submission_id": submission.id,
                    "candidate_name": submission.candidate_name,
                    "total_score": submission.total_score,
                    "status": "completed",
                },
                timeout=2.0,
            )
    except Exception as exc:
        logger.warning("Webhook fire failed for submission %s: %s", submission.id, exc)


async def process_evaluation_task(submission_id: str):
    async with AsyncSessionLocal() as db:
        submission = await db.get(Submission, submission_id)
        if not submission:
            return
        assertion_result = await db.execute(
            select(Assertion)
            .where(Assertion.question_id == submission.question_id)
            .order_by(Assertion.order)
        )
        assertions = list(assertion_result.scalars().all())
        submission.status = SubmissionStatus.evaluating
        await db.commit()
        try:
            if not assertions:
                raise ValueError("The published question has no assertions")
            if any(item.last_validation_status != "passed" for item in assertions):
                raise ValueError("The assertion set has not passed reference stability validation")

            results = await evaluate_submission(
                html=submission.submitted_html or "",
                css=submission.submitted_css or "",
                js=submission.submitted_js or "",
                assertions=assertions,
            )
            await db.execute(delete(EvaluationResult).where(EvaluationResult.submission_id == submission.id))
            assertion_map = {item.id: item for item in assertions}
            passed_count = 0
            earned = 0
            needs_review = False
            evidence = []
            for result in results:
                assertion = assertion_map[result["assertion_id"]]
                status = str(result.get("status") or "").lower()
                error_text = result.get("error") or ""
                reason_text = result.get("reason") or ""
                if status == "error" or "timeout" in error_text.lower() or "timeout" in reason_text.lower():
                    needs_review = True
                tc_status = (
                    TCStatus.passed if status == "pass"
                    else TCStatus.skipped if status == "skipped"
                    else TCStatus.failed
                )
                points = int(result.get("points_awarded") or 0)
                if tc_status == TCStatus.passed:
                    passed_count += 1
                earned += points
                db.add(EvaluationResult(
                    submission_id=submission.id,
                    assertion_id=assertion.id,
                    assertion_set_version=assertion.assertion_set_version,
                    tc_status=tc_status,
                    actual_result=result.get("actual_value"),
                    evidence_text=error_text or "Passed.",
                    blocked_by_assertion_id=result.get("blocked_by"),
                    points_awarded=points,
                ))
                evidence.append({
                    "assertion_id": assertion.id,
                    "status": status,
                    "expected": assertion.expected_value,
                    "actual": result.get("actual_value"),
                    "operator": assertion.operator.value if hasattr(assertion.operator, "value") else assertion.operator,
                    "points_awarded": points,
                    "blocked_by": result.get("blocked_by"),
                    "message": error_text or "Passed.",
                })

            max_score = sum(item.points for item in assertions)
            deterministic_summary = (
                f"Playwright passed {passed_count} of {len(assertions)} assertions "
                f"and awarded {earned} of {max_score} points."
            )
            try:
                advisory_summary = await asyncio.wait_for(
                    generate_eval_feedback(earned, max_score, evidence),
                    timeout=20.0,
                )
            except Exception:
                advisory_summary = ""
            submission.tc_passed = passed_count
            submission.tc_total = len(assertions)
            submission.total_score = earned
            submission.max_score = max_score
            submission.ai_feedback_text = advisory_summary or deterministic_summary
            submission.ai_feedback_breakdown = json.dumps({
                "summary": deterministic_summary,
                "advisory_feedback": advisory_summary,
                "assertions": evidence,
            })
            submission.ai_confidence = None
            submission.needs_review = needs_review
            submission.status = SubmissionStatus.completed
            submission.evaluated_at = datetime.utcnow()
        except Exception as exc:
            logger.exception("Evaluation failed for submission %s", submission_id)
            submission.status = SubmissionStatus.failed
            submission.ai_feedback_text = f"Playwright evaluation failed: {exc}"
            submission.needs_review = True
        finally:
            await db.commit()

        if submission.status == SubmissionStatus.completed:
            await _fire_webhook(submission)
