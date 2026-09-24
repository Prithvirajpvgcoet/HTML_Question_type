import re
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from database import get_db
from models import Question, Assertion
from models.question import ValidationStatus
from services.assertion_service.generator import generate_assertions_from_llm
from services.evaluation_service.runner import evaluate_submission

logger = logging.getLogger(__name__)


router = APIRouter()

class CreateQuestionReq(BaseModel):
    title: str
    description_html: str = ""
    question_type: str = "HTML/CSS/JS"
    is_published: bool = False

class UpdateCodeSolutionReq(BaseModel):
    reference_html: str = ""
    reference_css: str = ""
    reference_js: str = ""

@router.post("")
async def create_question(req: CreateQuestionReq, db: AsyncSession = Depends(get_db)):
    new_q = Question(
        title=req.title,
        description_html=req.description_html,
        question_type=req.question_type
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

@router.put("/{question_id}/code-solution")
async def update_code_solution(
    question_id: str, 
    req: UpdateCodeSolutionReq, 
    db: AsyncSession = Depends(get_db)
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

async def _validate_against_reference(
    q: Question,
    saved_assertions: list,
    db: AsyncSession
) -> None:
    """
    Runs saved_assertions against q's reference solution via the Playwright evaluator.
    
    If all assertions pass  → marks q.validation_status = passed and commits.
    If any assertion fails  → raises HTTPException 400 with structured failure details.
    
    This is the ground-truth gate: a correct reference solution must always pass
    its own generated assertions. Any failure here means the assertions are wrong,
    not the reference code.
    """
    results = await evaluate_submission(
        html=q.reference_html or "",
        css=q.reference_css or "",
        js=q.reference_js or "",
        assertions=saved_assertions
    )

    failed = [r for r in results if not r["passed"]]

    if not failed:
        # All assertions pass — mark the question as validated
        q.validation_status = ValidationStatus.passed
        q.last_validation_results = json.dumps(results)
        await db.commit()
        logger.info("reference_validation_passed", extra={"question_id": q.id})
        return

    # Build structured failure details with actionable hints
    failure_details = []
    for r in failed:
        failure_details.append({
            "assertion_id": r["assertion_id"],
            "error": r.get("error", ""),
            "hint": (
                "If the button/element is still in a wrong state, check that ALL "
                "input fields the reference JS reads in its enabling condition are "
                "included as setup steps (trigger: input/change) in this group, "
                "in sequence, before this assertion."
            )
        })

    logger.warning(
        "reference_validation_failed",
        extra={"question_id": q.id, "failed_count": len(failed)}
    )

    raise HTTPException(
        status_code=400,
        detail={
            "type": "reference_solution_mismatch",
            "message": (
                f"{len(failed)} of {len(results)} assertions fail against your own "
                "reference solution. This means the assertions are incomplete or wrong "
                "— not the reference code. Regenerate assertions to fix."
            ),
            "failures": failure_details,
            "total_failed": len(failed),
            "total_assertions": len(results)
        }
    )


@router.post("/{question_id}/generate-assertions")
async def generate_assertions(question_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    # 1. Get the question and reference solution
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if not q.reference_html:
        raise HTTPException(status_code=400, detail="A reference HTML solution must be saved before generating assertions.")
        
    # 2. Call LLM
    raw_assertions = await generate_assertions_from_llm(
        title=q.title,
        description=q.description_html,
        html=q.reference_html,
        css=q.reference_css,
        js=q.reference_js
    )
    
    # 3. Validate generated assertions
    issues = []
    if len(raw_assertions) < 5:
        issues.append({"type": "count", "message": f"Only {len(raw_assertions)} assertions generated; need >= 5."})
    
    if issues:
        raise HTTPException(status_code=400, detail={"message": "Generated assertions failed validation.", "issues": issues})
        
    # 4. Delete existing assertions and their evaluation results (to avoid FK violation)
    from sqlalchemy import text
    await db.execute(
        text("DELETE FROM evaluation_results WHERE assertion_id IN (SELECT id FROM assertions WHERE question_id=:qid)"),
        {"qid": question_id}
    )
    await db.execute(delete(Assertion).where(Assertion.question_id == question_id))
    
    # Also reset validation_status on the question
    q.validation_status = ValidationStatus.not_run
    q.is_published = False
    
    await db.commit()

    # 4. Save them to DB
    saved_assertions = []
    for i, a_data in enumerate(raw_assertions):
        new_assert = Assertion(
            question_id=q.id,
            order=i,
            trigger=a_data.get("trigger", "page_load"),
            trigger_selector=a_data.get("trigger_selector", ""), 
            check_selector=a_data.get("check_selector", ""),
            check_type=a_data.get("check_type", "dom_presence"),
            expected_result=a_data.get("expected_result", ""),
            points=a_data.get("points", 10),
            wait_ms=a_data.get("wait_ms", 300),
            is_sample=a_data.get("is_sample", False),
            execution_mode=a_data.get("execution_mode", "isolated"),
            group_id=a_data.get("group_id"),
            sequence_order=a_data.get("sequence_order"),
            depends_on_state=a_data.get("depends_on_state")
        )
        db.add(new_assert)
        saved_assertions.append(new_assert)
        
    await db.commit()
    for obj in saved_assertions:
        await db.refresh(obj)

    # 5. Gate: run assertions against reference solution.
    #    A correct reference must pass its own test cases.
    #    If it fails, the assertions are wrong — roll back and report.
    try:
        await _validate_against_reference(q, saved_assertions, db)
    except HTTPException as validation_error:
        # Rollback: remove the broken assertion set so nothing bad lands in DB
        from sqlalchemy import delete as sa_delete
        await db.execute(sa_delete(Assertion).where(Assertion.question_id == question_id))
        q.validation_status = ValidationStatus.failed
        q.is_published = False
        await db.commit()
        raise validation_error

    return {
        "message": "Generated successfully", 
        "assertions": [
            {
                "id": a.id, "trigger": a.trigger, "trigger_selector": a.trigger_selector, "check_selector": a.check_selector,
                "check_type": a.check_type, "expected_result": a.expected_result, "points": a.points
            }
            for a in saved_assertions
        ]
    }

@router.get("/{question_id}/assertions")
async def get_assertions(question_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Assertion).where(Assertion.question_id == question_id).order_by(Assertion.order))
    return result.scalars().all()


class CreateAssertionReq(BaseModel):
    trigger: str = "page_load"
    trigger_selector: str
    check_selector: str
    check_type: str = "dom_presence"
    expected_result: str = ""
    points: int = 10
    is_sample: bool = False

@router.post("/{question_id}/assertions")
async def create_assertion(question_id: str, req: CreateAssertionReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Assertion).where(Assertion.question_id == question_id))
    existing = result.scalars().all()
    order = len(existing)

    new_assert = Assertion(
        question_id=question_id,
        order=order,
        trigger=req.trigger,
        trigger_selector=req.trigger_selector, check_selector=req.check_selector,
        check_type=req.check_type,
        expected_result=req.expected_result,
        points=req.points,
        is_sample=req.is_sample,
        source="author_added"
    )
    db.add(new_assert)
    await db.commit()
    await db.refresh(new_assert)
    return new_assert


class UpdateAssertionReq(BaseModel):
    trigger: str | None = None
    trigger_selector: str | None = None
    check_selector: str | None = None
    check_type: str | None = None
    expected_result: str | None = None
    points: int | None = None
    is_sample: bool | None = None

@router.put("/assertions/{assertion_id}")
async def update_assertion(assertion_id: str, req: UpdateAssertionReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Assertion).where(Assertion.id == assertion_id))
    assertion = result.scalar_one_or_none()
    if not assertion:
        raise HTTPException(status_code=404, detail="Assertion not found")
    if req.trigger is not None:
        assertion.trigger = req.trigger
    if req.trigger_selector is not None:
        assertion.trigger_selector = req.trigger_selector
    if req.check_selector is not None:
        assertion.check_selector = req.check_selector
    if req.check_type is not None:
        assertion.check_type = req.check_type
    if req.expected_result is not None:
        assertion.expected_result = req.expected_result
    if req.points is not None:
        assertion.points = req.points
    if req.is_sample is not None:
        assertion.is_sample = req.is_sample
    await db.commit()
    await db.refresh(assertion)
    return assertion

@router.delete("/assertions/{assertion_id}", status_code=204)
async def delete_assertion(assertion_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Assertion).where(Assertion.id == assertion_id))
    assertion = result.scalar_one_or_none()
    if not assertion:
        raise HTTPException(status_code=404, detail="Assertion not found")
    
    from sqlalchemy import text
    await db.execute(
        text("DELETE FROM evaluation_results WHERE assertion_id=:aid"),
        {"aid": assertion_id}
    )
    
    # Also invalidate the question since assertions changed
    q_res = await db.execute(select(Question).where(Question.id == assertion.question_id))
    q = q_res.scalar_one_or_none()
    if q:
        q.validation_status = ValidationStatus.not_run
        q.is_published = False
        
    await db.delete(assertion)
    await db.commit()
    return None



@router.get("")
async def list_questions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).order_by(Question.created_at.desc()))
    questions = result.scalars().all()
    return questions



@router.post("/{question_id}/code-solution/validate")
async def validate_reference_solution(question_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if not q.reference_html:
        raise HTTPException(status_code=400, detail="A reference HTML solution must be saved before validating assertions.")
        
    assert_res = await db.execute(select(Assertion).where(Assertion.question_id == question_id).order_by(Assertion.order))
    assertions = assert_res.scalars().all()
    
    if not assertions:
        return {"results": [], "all_passed": True}
        
    results = await evaluate_submission(
        html=q.reference_html or "",
        css=q.reference_css or "",
        js=q.reference_js or "",
        assertions=assertions
    )
    
    all_passed = all(r["passed"] for r in results)
    
    q.validation_status = ValidationStatus.passed if all_passed else ValidationStatus.failed
    q.last_validation_results = json.dumps(results)
    await db.commit()
    
    return {"results": results, "all_passed": all_passed}

@router.get("/{question_id}/export")
async def export_question(question_id: str, db: AsyncSession = Depends(get_db)):
    q_res = await db.execute(select(Question).where(Question.id == question_id))
    q = q_res.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404)
        
    a_res = await db.execute(select(Assertion).where(Assertion.question_id == question_id))
    assertions = a_res.scalars().all()
    
    return {
        "version": "1.0",
        "question": {
            "title": q.title,
            "description_html": q.description_html,
            "question_type": q.question_type,
            "reference_html": q.reference_html,
            "reference_css": q.reference_css,
            "reference_js": q.reference_js
        },
        "assertions": [{"trigger": a.trigger, "trigger_selector": a.trigger_selector, "check_selector": a.check_selector, "check_type": a.check_type, "expected_result": a.expected_result, "points": a.points} for a in assertions]
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
        reference_js=q_data.get("reference_js", "")
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    
    assertions_data = data.get("assertions", [])
    for i, a in enumerate(assertions_data):
        new_a = Assertion(
            question_id=q.id,
            order=i,
            trigger=a.get("trigger", "page_load"),
            trigger_selector=a.get("trigger_selector", ""), check_selector=a.get("check_selector", ""),
            check_type=a.get("check_type", "dom_presence"),
            expected_result=a.get("expected_result", ""),
            points=a.get("points", 5)
        )
        db.add(new_a)
    await db.commit()
    return {"id": q.id, "message": "Imported successfully"}


@router.put("/{question_id}")
async def update_question(
    question_id: str, 
    req: CreateQuestionReq, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if req.is_published and not q.reference_html:
        raise HTTPException(status_code=400, detail="A reference HTML solution must be saved before publishing.")
    if req.is_published:
        # Hard gate: actively re-run assertions against reference solution.
        # Checking validation_status alone is not enough — it can go stale
        # if assertions or the reference solution were edited after last validation.
        assert_res = await db.execute(
            select(Assertion)
            .where(Assertion.question_id == question_id)
            .order_by(Assertion.order)
        )
        current_assertions = assert_res.scalars().all()
        if not current_assertions:
            raise HTTPException(
                status_code=400,
                detail="Cannot publish a question with no assertions. Generate assertions first."
            )
        # This will raise 400 if reference fails its own assertions
        await _validate_against_reference(q, list(current_assertions), db)
    
    q.title = req.title
    q.description_html = req.description_html
    q.question_type = req.question_type
    q.is_published = req.is_published
    
    await db.commit()
    await db.refresh(q)
    return q


