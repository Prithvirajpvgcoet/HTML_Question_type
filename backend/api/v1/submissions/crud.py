from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from database import get_db
from models import Submission, EvaluationResult, SubmissionStatus, Assertion
from services.evaluation_service.worker import process_evaluation_task

router = APIRouter()

@router.get("")
async def list_submissions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Submission).order_by(Submission.submitted_at.desc()))
    return result.scalars().all()

class CreateSubmissionReq(BaseModel):
    question_id: str
    candidate_name: str = "Test Candidate"
    submitted_html: str = ""
    submitted_css: str = ""
    submitted_js: str = ""


@router.post("")
async def create_submission(req: CreateSubmissionReq, db: AsyncSession = Depends(get_db)):
    sub = Submission(
        question_id=req.question_id,
        candidate_name=req.candidate_name,
        submitted_html=req.submitted_html,
        submitted_css=req.submitted_css,
        submitted_js=req.submitted_js,
        status=SubmissionStatus.pending
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {"id": sub.id, "status": sub.status, "candidate_name": sub.candidate_name}


@router.post("/{submission_id}/evaluate")
async def trigger_evaluation(
    submission_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    background_tasks.add_task(process_evaluation_task, submission_id)
    return {"message": "Evaluation queued.", "submission_id": submission_id}


@router.get("/{submission_id}/evaluation")
async def get_evaluation_report(submission_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.evaluation_results))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Fetch all assertions for this question to enrich the report
    assertions_result = await db.execute(
        select(Assertion).where(Assertion.question_id == submission.question_id)
    )
    assertions = {a.id: a for a in assertions_result.scalars().all()}

    results = []
    for r in submission.evaluation_results:
        a = assertions.get(r.assertion_id)
        results.append({
            "assertion_id": r.assertion_id,
            "status": r.tc_status,
            "actual_result": r.actual_result,
            "points_awarded": r.points_awarded,
            "llm_status": r.llm_status,
            "llm_evidence": r.llm_evidence_text,
            # Assertion details
            "assertion_trigger": a.trigger if a else None,
            "assertion_check_type": a.check_type if a else None,
            "assertion_expected": a.expected_result if a else None,
            "assertion_points": a.points if a else 0,
            "assertion_is_sample": a.is_sample if a else False,
            "assertion_trigger_selector": a.trigger_selector if a else None, "assertion_check_selector": a.check_selector if a else None,
        })

    import json
    breakdown = {}
    if submission.ai_feedback_breakdown:
        try:
            breakdown = json.loads(submission.ai_feedback_breakdown)
        except json.JSONDecodeError:
            pass

    return {
        "id": submission.id,
        "candidate_name": submission.candidate_name,
        "status": submission.status,
        "total_score": submission.total_score,
        "max_score": submission.max_score,
        "tc_passed": submission.tc_passed,
        "tc_total": submission.tc_total,
        "ai_feedback_text": submission.ai_feedback_text,
        "ai_feedback_breakdown": breakdown,
        "needs_review": submission.needs_review,
        "submitted_html": submission.submitted_html,
        "submitted_css": submission.submitted_css,
        "submitted_js": submission.submitted_js,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "evaluated_at": submission.evaluated_at.isoformat() if submission.evaluated_at else None,
        "results": results
    }

class ReviewReq(BaseModel):
    needs_review: bool


@router.put("/{submission_id}/review")
async def toggle_review_flag(
    submission_id: str,
    req: ReviewReq,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.needs_review = req.needs_review
    await db.commit()
    return {"message": "Review flag updated", "needs_review": submission.needs_review}
