import json
import asyncio
import logging
import re
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import delete as sa_delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from database import get_db, AsyncSessionLocal
from models import Question, Assertion, AssertionGenerationJob
from models.assertion_job import JobStatus
from models.question import ValidationStatus
from services.assertion_service.generator import generate_assertions_from_llm, generate_edge_cases_from_llm
from services.evaluation_service.runner import evaluate_submission

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_REPAIR_ROUNDS = 2


class QuestionPublic(BaseModel):
    id: str
    title: str
    description_html: str
    purpose: str | None = None
    question_type: str | None = None
    starter_html: str | None = None
    starter_css: str | None = None
    starter_js: str | None = None
    question_bank_name: str | None = None
    is_published: bool

@router.get("/{question_id}/public", response_model=QuestionPublic)
async def get_question_public(question_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q

EMPTY_SUBMISSION_MAX_SCORE_PCT = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_assertion(a: Assertion) -> dict:
    return {
        "id": a.id,
        "trigger": a.trigger.value if hasattr(a.trigger, "value") else a.trigger,
        "trigger_selector": a.trigger_selector,
        "check_selector": a.check_selector,
        "check_type": a.check_type.value if hasattr(a.check_type, "value") else a.check_type,
        "input_value": a.input_value,
        "property_name": a.property_name,
        "operator": a.operator.value if hasattr(a.operator, "value") else a.operator,
        "expected_value": a.expected_value,
        "points": a.points,
        "is_sample": a.is_sample,
        "wait_ms": a.wait_ms,
        "execution_mode": a.execution_mode.value if hasattr(a.execution_mode, "value") else a.execution_mode,
        "group_id": a.group_id,
        "sequence_order": a.sequence_order,
        "last_validation_status": getattr(a, "last_validation_status", "not_run"),
        "last_validation_error": getattr(a, "last_validation_error", None),
        "assertion_set_version": getattr(a, "assertion_set_version", 1),
    }


async def _validate_against_reference(
    q: Question,
    saved_assertions: list,
    db: AsyncSession,
) -> dict:
    """
    Runs saved_assertions against q's reference solution via Playwright.
    Writes last_validation_status / last_validation_error on every row.
    Returns {"passed": [...], "failed": [...]} — never raises.
    """
    run_one = await evaluate_submission(
        html=q.reference_html or "",
        css=q.reference_css or "",
        js=q.reference_js or "",
        assertions=saved_assertions,
        capture_only=True,
    )
    run_two = await evaluate_submission(
        html=q.reference_html or "",
        css=q.reference_css or "",
        js=q.reference_js or "",
        assertions=saved_assertions,
        capture_only=True,
    )
    first = {r["assertion_id"]: r for r in run_one}
    second = {r["assertion_id"]: r for r in run_two}

    passed, failed = [], []
    for a in saved_assertions:
        r1, r2 = first.get(a.id), second.get(a.id)
        stable = bool(
            r1 and r2 and r1["passed"] and r2["passed"]
            and r1.get("actual_value") == r2.get("actual_value")
        )
        actual = r1.get("actual_value") if r1 else None
        operator = a.operator.value if hasattr(a.operator, "value") else str(a.operator)
        if stable and operator == "equals":
            a.expected_value = actual
        elif stable and operator == "contains":
            stable = str(a.expected_value or "") in str(actual or "")
        elif stable and operator == "regex":
            try:
                stable = re.search(str(a.expected_value or ""), str(actual or "")) is not None
            except re.error:
                stable = False
        elif stable and operator == "exists":
            stable = actual not in (None, "False", False)
        elif stable and operator == "not_exists":
            stable = actual in ("True", True)

        if stable:
            a.last_validation_status = "passed"
            a.last_validation_error = None
            passed.append(a)
        else:
            values_differ = bool(r1 and r2 and r1.get("actual_value") != r2.get("actual_value"))
            a.last_validation_status = "flaky" if values_differ else "failed"
            a.last_validation_error = (
                f"Unstable reference values: {r1.get('actual_value')!r} then {r2.get('actual_value')!r}"
                if values_differ else (r1 or r2 or {}).get("error", "Reference assertion did not pass")
            )
            failed.append(a)

    empty_run = []
    empty_score_pct = 0.0
    if saved_assertions and not failed:
        empty_run = await evaluate_submission(
            html="",
            css="",
            js="",
            assertions=saved_assertions,
            capture_only=False,
        )
        max_points = sum(int(getattr(item, "points", 0) or 0) for item in saved_assertions)
        empty_points = sum(int(item.get("points_awarded") or 0) for item in empty_run)
        empty_score_pct = round((empty_points / max_points) * 100, 1) if max_points else 0.0
        if empty_score_pct > EMPTY_SUBMISSION_MAX_SCORE_PCT:
            false_positive_ids = {
                item.get("assertion_id")
                for item in empty_run
                if int(item.get("points_awarded") or 0) > 0
            }
            sanity_error = (
                f"Negative sanity check failed: an empty submission scored "
                f"{empty_score_pct}% against this assertion set."
            )
            failed = []
            passed = []
            for a in saved_assertions:
                a.last_validation_status = "failed"
                a.last_validation_error = (
                    sanity_error if a.id in false_positive_ids
                    else f"{sanity_error} Review the full assertion set; this assertion was not individually awarded points."
                )
                failed.append(a)

    q.validation_status = ValidationStatus.passed if not failed else ValidationStatus.failed
    q.last_validation_results = json.dumps({
        "run_1": run_one,
        "run_2": run_two,
        "negative_sanity": {
            "threshold_pct": EMPTY_SUBMISSION_MAX_SCORE_PCT,
            "score_pct": empty_score_pct,
            "results": empty_run,
        },
    })
    await db.commit()
    for a in saved_assertions:
        await db.refresh(a)

    logger.info(
        "reference_validation_done",
        extra={"question_id": q.id, "passed": len(passed), "failed": len(failed)},
    )
    return {"passed": passed, "failed": failed}


async def _save_new_assertions(
    q: Question,
    raw_list: list[dict],
    order_offset: int,
    db: AsyncSession,
) -> list[Assertion]:
    """Persist a list of raw LLM-generated dicts as Assertion rows."""
    rows = []
    for idx, raw in enumerate(raw_list):
        new_a = Assertion(
            question_id=q.id,
            order=order_offset + idx,
            trigger=raw.get("trigger", "page_load"),
            trigger_selector=raw.get("trigger_selector", ""),
            check_selector=raw.get("check_selector", ""),
            check_type=raw.get("check_type", "dom_presence"),
            input_value=raw.get("input_value"),
            property_name=raw.get("property_name"),
            operator=raw.get("operator", "equals"),
            expected_value=raw.get("expected_value"),
            points=raw.get("points", 10),
            wait_ms=raw.get("wait_ms", 300),
            is_sample=raw.get("is_sample", False),
            execution_mode=raw.get("execution_mode", "isolated"),
            group_id=raw.get("group_id"),
            sequence_order=raw.get("sequence_order"),
            depends_on_state=raw.get("depends_on_state"),
            last_validation_status="not_run",
        )
        db.add(new_a)
        rows.append(new_a)
    await db.commit()
    for r in rows:
        await db.refresh(r)
    return rows


def _build_job_response(job: AssertionGenerationJob, assertions: list[dict] | None = None) -> dict:
    elapsed = (datetime.utcnow() - job.started_at).total_seconds()
    resp: dict = {
        "job_id": job.id,
        "status": job.status.value if hasattr(job.status, "value") else job.status,
        "mode": job.mode,
        "elapsed_seconds": round(elapsed, 1),
        "error_message": job.error_message,
        "repair_round": job.repair_round,
    }
    if assertions is not None:
        resp["assertions"] = assertions
    return resp


# ---------------------------------------------------------------------------
# Background job runner
# ---------------------------------------------------------------------------

async def _run_generation_job(
    job_id: str,
    question_id: str,
    mode: str,
    keep_ids: list[str] | None,
    failed_ids: list[str] | None,
    target_count: int,
    repair_round: int,
):
    """
    Heavy-lifting background task.  Uses its own DB session (BackgroundTasks
    in FastAPI run after the request session closes).
    """
    async with AsyncSessionLocal() as db:
        job = await db.get(AssertionGenerationJob, job_id)
        q_res = await db.execute(select(Question).where(Question.id == question_id))
        q = q_res.scalar_one_or_none()
        if not q or not job:
            return

        try:
            # ── Step 1: analyzing ──────────────────────────────────────────
            job.status = JobStatus.analyzing
            await db.commit()

            # Load keep assertions if provided
            keep_assertions_db: list[Assertion] = []
            if keep_ids:
                res = await db.execute(select(Assertion).where(Assertion.id.in_(keep_ids)))
                keep_assertions_db = list(res.scalars().all())

            failed_assertions_db: list[Assertion] = []
            if failed_ids:
                res = await db.execute(select(Assertion).where(Assertion.id.in_(failed_ids)))
                failed_assertions_db = list(res.scalars().all())

            keep_dicts = [_serialize_assertion(a) for a in keep_assertions_db]
            failed_dicts = [
                {**_serialize_assertion(a), "error": a.last_validation_error or ""}
                for a in failed_assertions_db
            ]

            # Staged generation: We DO NOT delete the old assertions here anymore.
            # We wait until the LLM returns successfully to prevent data loss on timeout/failure.
            pass

            # ── LLM call (hard timeout 90 s) ──────────────────────────────
            if mode == "edge_cases":
                raw = await asyncio.wait_for(
                    generate_edge_cases_from_llm(
                        title=q.title,
                        description=q.description_html,
                        existing_assertions=keep_dicts or [],
                        html=q.reference_html or "",
                        css=q.reference_css or "",
                        js=q.reference_js or "",
                    ),
                    timeout=90.0,
                )
            else:
                raw = await asyncio.wait_for(
                    generate_assertions_from_llm(
                        title=q.title,
                        description=q.description_html,
                        html=q.reference_html or "",
                        css=q.reference_css or "",
                        js=q.reference_js or "",
                        keep_assertions=keep_dicts or None,
                        failed_context=failed_dicts or None,
                        target_count=target_count,
                        mode=mode,
                    ),
                    timeout=90.0,
                )

            # ── Step 2: save & validate ───────────────────────────────────
            job.status = JobStatus.validating
            await db.commit()

            order_offset = len(keep_assertions_db)
            new_rows = await _save_new_assertions(q, raw, order_offset, db)
            all_assertions = keep_assertions_db + new_rows
            if all_assertions:
                base_points, remainder = divmod(100, len(all_assertions))
                for index, assertion in enumerate(all_assertions):
                    assertion.points = base_points + (1 if index < remainder else 0)

            split = await _validate_against_reference(q, all_assertions, db)

            job.status = JobStatus.completed
            job.finished_at = datetime.utcnow()
            # Store the split counts for the poll endpoint
            job.error_message = json.dumps({
                "passed_count": len(split["passed"]),
                "failed_count": len(split["failed"]),
            })
            await db.commit()

        except asyncio.TimeoutError:
            job.status = JobStatus.failed
            job.error_message = "LLM call timed out after 90 s. Try again."
            job.finished_at = datetime.utcnow()
            q.validation_status = ValidationStatus.failed
            await db.commit()
            logger.error("assertion_job_timeout", extra={"job_id": job_id})

        except Exception as exc:
            job.status = JobStatus.failed
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            q.validation_status = ValidationStatus.failed
            await db.commit()
            logger.error("assertion_job_failed", extra={"job_id": job_id, "error": str(exc)}, exc_info=True)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class UpdateQuestionReq(BaseModel):
    title: str
    description_html: str = ""
    purpose: str | None = None
    question_type: str = "HTML/CSS/JS"
    question_bank_name: str | None = None
    starter_html: str | None = None
    starter_css: str | None = None
    starter_js: str | None = None
    is_published: bool | None = None

class CreateQuestionReq(BaseModel):
    title: str
    description_html: str = ""
    question_type: str = "HTML/CSS/JS"
    is_published: bool = False


class UpdateCodeSolutionReq(BaseModel):
    reference_html: str = ""
    reference_css: str = ""
    reference_js: str = ""


class CompleteAssertionsReq(BaseModel):
    keep_assertion_ids: list[str]
    target_count: int = 6


class RepairAssertionsReq(BaseModel):
    failed_assertion_ids: list[str]
    keep_assertion_ids: list[str]
    assertion_set_version: int  # optimistic-concurrency guard


class CreateAssertionReq(BaseModel):
    trigger: Literal["page_load", "click", "input", "change", "hover", "call_function"] = "page_load"
    trigger_selector: Optional[str] = None
    input_value: Optional[str] = None
    check_selector: str
    check_type: Literal["dom_presence", "dom_absence", "element_count", "text_content", "attribute", "computed_style", "function_presence"] = "dom_presence"
    property_name: Optional[str] = None
    operator: Literal["equals", "contains", "regex", "exists", "not_exists"] = "equals"
    expected_value: Optional[str] = None
    points: int = 10
    is_sample: bool = False
    execution_mode: Literal["isolated", "sequential"] = "isolated"
    group_id: Optional[str] = None
    sequence_order: Optional[int] = None
    wait_ms: int = 0


class UpdateAssertionReq(BaseModel):
    trigger: Optional[Literal["page_load", "click", "input", "change", "hover", "call_function"]] = None
    trigger_selector: Optional[str] = None
    input_value: Optional[str] = None
    check_selector: Optional[str] = None
    check_type: Optional[Literal["dom_presence", "dom_absence", "element_count", "text_content", "attribute", "computed_style", "function_presence"]] = None
    property_name: Optional[str] = None
    operator: Optional[Literal["equals", "contains", "regex", "exists", "not_exists"]] = None
    expected_value: Optional[str] = None
    points: Optional[int] = None
    is_sample: Optional[bool] = None
    execution_mode: Optional[Literal["isolated", "sequential"]] = None
    group_id: Optional[str] = None
    sequence_order: Optional[int] = None
    wait_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("")
async def create_question(req: CreateQuestionReq, db: AsyncSession = Depends(get_db)):
    new_q = Question(
        title=req.title,
        description_html=req.description_html,
        question_type=req.question_type,
    )
    db.add(new_q)
    await db.commit()
    await db.refresh(new_q)
    return new_q


@router.get("/{question_id}")
async def get_question(question_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.get("")
async def list_questions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).order_by(Question.created_at.desc()))
    return result.scalars().all()


@router.put("/{question_id}/code-solution")
async def update_code_solution(
    question_id: str,
    req: UpdateCodeSolutionReq,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.reference_html = req.reference_html
    q.reference_css = req.reference_css
    q.reference_js = req.reference_js
    await db.commit()
    return {"status": "ok"}


@router.put("/{question_id}")
async def update_question(
    question_id: str,
    req: CreateQuestionReq,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if req.is_published and not q.reference_html:
        raise HTTPException(status_code=400, detail="A reference HTML solution must be saved before publishing.")
    if req.is_published:
        assert_res = await db.execute(
            select(Assertion)
            .where(Assertion.question_id == question_id)
            .order_by(Assertion.order)
        )
        current_assertions = assert_res.scalars().all()
        if not current_assertions:
            raise HTTPException(
                status_code=400,
                detail="Cannot publish a question with no assertions. Generate assertions first.",
            )
        split = await _validate_against_reference(q, list(current_assertions), db)
        if split["failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"{len(split['failed'])} assertions still fail against the reference solution. Fix them before publishing.",
            )

    q.title = req.title
    q.description_html = req.description_html
    q.question_type = req.question_type
    q.is_published = req.is_published
    await db.commit()
    await db.refresh(q)
    return q


# ── Assertion generation (async job-based) ─────────────────────────────────

@router.post("/{question_id}/generate-assertions")
async def generate_assertions(
    question_id: str,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if not q.reference_html:
        raise HTTPException(
            status_code=400,
            detail="A reference HTML solution must be saved before generating assertions.",
        )

    from datetime import timedelta
    # Job Reaper: auto-fail any active jobs older than 5 minutes
    stale_cutoff = datetime.utcnow() - timedelta(minutes=5)
    await db.execute(
        text("UPDATE assertion_generation_jobs SET status = 'failed', error_message = 'Job timed out unexpectedly' "
             "WHERE question_id = :qid AND status IN ('queued', 'analyzing', 'validating') AND started_at < :cutoff"),
        {"qid": question_id, "cutoff": stale_cutoff}
    )
    await db.commit()

    # Concurrency guard: one active job per question
    active = await db.execute(
        select(AssertionGenerationJob).where(
            AssertionGenerationJob.question_id == question_id,
            AssertionGenerationJob.status.in_(
                [JobStatus.queued, JobStatus.analyzing, JobStatus.validating]
            ),
        )
    )
    if active.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A generation job is already running for this question.")

    job = AssertionGenerationJob(question_id=question_id, mode="full", target_count=6)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    bg.add_task(
        _run_generation_job,
        job.id, question_id, "full", None, None, 6, 0,
    )
    return _build_job_response(job)


@router.post("/{question_id}/assertions/complete")
async def complete_assertions(
    question_id: str,
    req: CompleteAssertionsReq,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Button 1: keep passing assertions, fill quota with NEW diverse ones."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    active = await db.execute(
        select(AssertionGenerationJob).where(
            AssertionGenerationJob.question_id == question_id,
            AssertionGenerationJob.status.in_(
                [JobStatus.queued, JobStatus.analyzing, JobStatus.validating]
            ),
        )
    )
    if active.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A generation job is already running.")

    job = AssertionGenerationJob(
        question_id=question_id,
        mode="diversify",
        keep_assertion_ids=json.dumps(req.keep_assertion_ids),
        target_count=req.target_count,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    bg.add_task(
        _run_generation_job,
        job.id, question_id, "diversify",
        req.keep_assertion_ids, None, req.target_count, 0,
    )
    return _build_job_response(job)


@router.post("/{question_id}/assertions/repair")
async def repair_assertions(
    question_id: str,
    req: RepairAssertionsReq,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Button 2: keep passing assertions, regenerate replacements for the failed ones."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    # Optimistic-concurrency guard: reject if assertion set has changed since client last saw it
    sample_res = await db.execute(
        select(Assertion).where(Assertion.id.in_(req.keep_assertion_ids)).limit(1)
    )
    sample = sample_res.scalar_one_or_none()
    if sample and sample.assertion_set_version != req.assertion_set_version:
        raise HTTPException(
            status_code=409,
            detail="Assertion set has changed since you last loaded this page. Refresh and try again.",
        )

    active = await db.execute(
        select(AssertionGenerationJob).where(
            AssertionGenerationJob.question_id == question_id,
            AssertionGenerationJob.status.in_(
                [JobStatus.queued, JobStatus.analyzing, JobStatus.validating]
            ),
        )
    )
    if active.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A generation job is already running.")

    # Count how many repair rounds already happened
    recent_repairs = await db.execute(
        select(AssertionGenerationJob).where(
            AssertionGenerationJob.question_id == question_id,
            AssertionGenerationJob.mode == "repair",
            AssertionGenerationJob.status == JobStatus.completed,
        )
    )
    round_count = len(recent_repairs.scalars().all())
    if round_count >= MAX_REPAIR_ROUNDS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Auto-repair has been attempted {round_count} times for this assertion set. "
                "Please edit the failing assertions manually using the edit button."
            ),
        )

    target_count = len(req.keep_assertion_ids) + len(req.failed_assertion_ids)
    job = AssertionGenerationJob(
        question_id=question_id,
        mode="repair",
        keep_assertion_ids=json.dumps(req.keep_assertion_ids),
        failed_assertion_ids=json.dumps(req.failed_assertion_ids),
        target_count=target_count,
        repair_round=round_count + 1,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    bg.add_task(
        _run_generation_job,
        job.id, question_id, "repair",
        req.keep_assertion_ids, req.failed_assertion_ids, target_count, round_count + 1,
    )
    return _build_job_response(job)


@router.post("/{question_id}/generation-jobs/{job_id}/cancel")
async def cancel_job(
    question_id: str,
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel an in-flight job (marks it cancelled; the background task checks this flag)."""
    job = await db.get(AssertionGenerationJob, job_id)
    if not job or job.question_id != question_id:
        raise HTTPException(status_code=404)
    if job.status not in (JobStatus.queued, JobStatus.analyzing, JobStatus.validating):
        raise HTTPException(status_code=409, detail="Job is not in a cancellable state.")
    job.status = JobStatus.cancelled
    job.finished_at = datetime.utcnow()
    await db.commit()
    return {"status": "cancelled"}


@router.get("/{question_id}/generation-jobs/active")
async def get_active_job(question_id: str, db: AsyncSession = Depends(get_db)):
    """Return the most recent in-flight or completed job for this question."""
    res = await db.execute(
        select(AssertionGenerationJob)
        .where(AssertionGenerationJob.question_id == question_id)
        .order_by(AssertionGenerationJob.started_at.desc())
        .limit(1)
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="No job found")

    payload = _build_job_response(job)

    # If completed, also include the current assertions so the frontend can render immediately
    if job.status == JobStatus.completed:
        a_res = await db.execute(
            select(Assertion)
            .where(Assertion.question_id == question_id)
            .order_by(Assertion.order)
        )
        assertions = a_res.scalars().all()
        payload["assertions"] = [_serialize_assertion(a) for a in assertions]
        # Parse pass/fail counts from the stored JSON in error_message
        try:
            counts = json.loads(job.error_message or "{}")
            payload["passed_count"] = counts.get("passed_count", 0)
            payload["failed_count"] = counts.get("failed_count", 0)
        except Exception:
            pass

    return payload


@router.get("/{question_id}/generation-jobs/{job_id}")
async def get_job_status(
    question_id: str,
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(AssertionGenerationJob, job_id)
    if not job or job.question_id != question_id:
        raise HTTPException(status_code=404)

    payload = _build_job_response(job)

    if job.status == JobStatus.completed:
        a_res = await db.execute(
            select(Assertion)
            .where(Assertion.question_id == question_id)
            .order_by(Assertion.order)
        )
        assertions = a_res.scalars().all()
        payload["assertions"] = [_serialize_assertion(a) for a in assertions]
        try:
            counts = json.loads(job.error_message or "{}")
            payload["passed_count"] = counts.get("passed_count", 0)
            payload["failed_count"] = counts.get("failed_count", 0)
        except Exception:
            pass

    return payload


# ── Assertion CRUD ─────────────────────────────────────────────────────────

@router.get("/{question_id}/assertions")
async def get_assertions(question_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Assertion)
        .where(Assertion.question_id == question_id)
        .order_by(Assertion.order)
    )
    return [_serialize_assertion(a) for a in result.scalars().all()]


@router.post("/{question_id}/assertions")
async def create_assertion(
    question_id: str, req: CreateAssertionReq, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assertion).where(Assertion.question_id == question_id))
    order = len(result.scalars().all())
    new_a = Assertion(
        question_id=question_id,
        order=order,
        trigger=req.trigger,
        trigger_selector=req.trigger_selector,
        input_value=req.input_value,
        check_selector=req.check_selector,
        check_type=req.check_type,
        property_name=req.property_name,
        operator=req.operator,
        expected_value=req.expected_value,
        points=req.points,
        is_sample=req.is_sample,
        execution_mode=req.execution_mode,
        group_id=req.group_id,
        sequence_order=req.sequence_order,
        wait_ms=req.wait_ms,
        source="author_added",
    )
    db.add(new_a)
    await db.commit()
    await db.refresh(new_a)
    return _serialize_assertion(new_a)


@router.put("/assertions/{assertion_id}")
async def update_assertion(
    assertion_id: str, req: UpdateAssertionReq, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assertion).where(Assertion.id == assertion_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assertion not found")
    for field, val in req.model_dump(exclude_none=True).items():
        setattr(a, field, val)
    # Any manual edit resets validation status so the author knows to re-validate
    a.last_validation_status = "not_run"
    a.last_validation_error = None
    await db.commit()
    await db.refresh(a)
    return _serialize_assertion(a)


@router.delete("/assertions/{assertion_id}", status_code=204)
async def delete_assertion(assertion_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Assertion).where(Assertion.id == assertion_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assertion not found")
    await db.execute(
        text("DELETE FROM evaluation_results WHERE assertion_id=:aid"), {"aid": assertion_id}
    )
    q_res = await db.execute(select(Question).where(Question.id == a.question_id))
    q = q_res.scalar_one_or_none()
    if q:
        q.validation_status = ValidationStatus.not_run
        q.is_published = False
    await db.delete(a)
    await db.commit()


# ── Misc ───────────────────────────────────────────────────────────────────

@router.post("/{question_id}/generate-edge-cases")
async def generate_edge_cases(
    question_id: str,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if not q.reference_html:
        raise HTTPException(
            status_code=400,
            detail="A reference HTML solution must be saved before generating edge cases.",
        )

    from datetime import timedelta
    # Job Reaper: auto-fail any active jobs older than 5 minutes
    stale_cutoff = datetime.utcnow() - timedelta(minutes=5)
    await db.execute(
        text("UPDATE assertion_generation_jobs SET status = 'failed', error_message = 'Job timed out unexpectedly' "
             "WHERE question_id = :qid AND status IN ('queued', 'analyzing', 'validating') AND started_at < :cutoff"),
        {"qid": question_id, "cutoff": stale_cutoff}
    )
    await db.commit()

    # Concurrency guard: one active job per question
    active = await db.execute(
        select(AssertionGenerationJob).where(
            AssertionGenerationJob.question_id == question_id,
            AssertionGenerationJob.status.in_([JobStatus.queued, JobStatus.analyzing, JobStatus.validating]),
        )
    )
    if active.scalar_one_or_none():
        raise HTTPException(status_code=422, detail="An assertion generation job is already running.")

    # Create job
    job = AssertionGenerationJob(
        question_id=question_id,
        mode="edge_cases",
        target_count=2,  # The edge cases prompt asks for 2
        status=JobStatus.queued,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Keep all existing assertions when doing edge cases
    a_res = await db.execute(select(Assertion).where(Assertion.question_id == question_id))
    existing_ids = [a.id for a in a_res.scalars().all()]

    bg.add_task(
        _run_generation_job,
        job_id=job.id,
        question_id=question_id,
        mode="edge_cases",
        keep_ids=existing_ids,
        failed_ids=[],
        target_count=2,
        repair_round=0,
    )

    return _build_job_response(job)


@router.post("/{question_id}/code-solution/validate")
async def validate_reference_solution(question_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if not q.reference_html:
        raise HTTPException(status_code=400, detail="A reference HTML solution must be saved first.")
    a_res = await db.execute(
        select(Assertion).where(Assertion.question_id == question_id).order_by(Assertion.order)
    )
    assertions = a_res.scalars().all()
    if not assertions:
        return {"results": [], "all_passed": True}
    split = await _validate_against_reference(q, list(assertions), db)
    return {
        "results": [_serialize_assertion(a) for a in assertions],
        "all_passed": len(split["failed"]) == 0,
    }


@router.get("/{question_id}/export")
async def export_question(question_id: str, db: AsyncSession = Depends(get_db)):
    q_res = await db.execute(select(Question).where(Question.id == question_id))
    q = q_res.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404)
    a_res = await db.execute(select(Assertion).where(Assertion.question_id == question_id))
    return {
        "version": "1.0",
        "question": {
            "title": q.title,
            "description_html": q.description_html,
            "question_type": q.question_type,
            "reference_html": q.reference_html,
            "reference_css": q.reference_css,
            "reference_js": q.reference_js,
        },
        "assertions": [_serialize_assertion(a) for a in a_res.scalars().all()],
    }


@router.post("/import")
async def import_question(data: dict, db: AsyncSession = Depends(get_db)):
    if "question" not in data:
        raise HTTPException(status_code=400, detail="Invalid format")
    q_data = data["question"]
    q = Question(
        title=q_data.get("title", "Imported"),
        description_html=q_data.get("description_html", ""),
        question_type=q_data.get("question_type", "HTML/CSS/JS"),
        reference_html=q_data.get("reference_html", ""),
        reference_css=q_data.get("reference_css", ""),
        reference_js=q_data.get("reference_js", ""),
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    for i, a in enumerate(data.get("assertions", [])):
        db.add(
            Assertion(
                question_id=q.id,
                order=i,
                trigger=a.get("trigger", "page_load"),
                trigger_selector=a.get("trigger_selector", ""),
                input_value=a.get("input_value"),
                check_selector=a.get("check_selector", ""),
                check_type=a.get("check_type", "dom_presence"),
                property_name=a.get("property_name"),
                operator=a.get("operator", "equals"),
                expected_value=a.get("expected_value"),
                points=a.get("points", 5),
                execution_mode=a.get("execution_mode", "isolated"),
                group_id=a.get("group_id"),
                sequence_order=a.get("sequence_order"),
                wait_ms=a.get("wait_ms", 0),
            )
        )
    await db.commit()
    return {"id": q.id, "message": "Imported successfully"}
