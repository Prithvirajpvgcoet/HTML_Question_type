import re

with open('backend/api/v1/questions/crud.py', 'r', encoding='utf-8') as f:
    text = f.read()

endpoints = '''
# ----------------- PARTIAL RETENTION ENDPOINTS -----------------

async def _load_question_and_assertions(question_id: str, assertion_ids: list[str], db: AsyncSession):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalars().first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
        
    result = await db.execute(select(Assertion).where(Assertion.id.in_(assertion_ids)))
    assertions = result.scalars().all()
    return q, assertions

async def _save_and_revalidate(q: Question, keep_assertions: list[Assertion], new_raw: list[dict], db: AsyncSession):
    # Save the new assertions
    new_rows = []
    for idx, raw in enumerate(new_raw):
        new_a = Assertion(
            question_id=q.id,
            trigger=raw["trigger"],
            trigger_selector=raw.get("trigger_selector", ""),
            check_selector=raw.get("check_selector", ""),
            check_type=raw["check_type"],
            expected_result=raw.get("expected_result", ""),
            points=10,
            order=len(keep_assertions) + idx,
            last_validation_status="not_run"
        )
        db.add(new_a)
        new_rows.append(new_a)
        
    await db.commit()
    for row in new_rows:
        await db.refresh(row)
        
    # Revalidate all together
    all_assertions = keep_assertions + new_rows
    split = await _validate_against_reference(q, all_assertions, db)
    
    def serialize(a):
        return {
            "id": a.id, "trigger": a.trigger.value if hasattr(a.trigger, "value") else a.trigger, 
            "trigger_selector": a.trigger_selector, "check_selector": a.check_selector,
            "check_type": a.check_type.value if hasattr(a.check_type, "value") else a.check_type, 
            "expected_result": a.expected_result, "points": a.points,
            "last_validation_status": getattr(a, "last_validation_status", "not_run"),
            "last_validation_error": getattr(a, "last_validation_error", None)
        }
        
    return {
        "message": "Generated and validated",
        "passed_count": len(split["passed"]),
        "failed_count": len(split["failed"]),
        "assertions": [serialize(a) for a in all_assertions],
    }

class CompleteAssertionsReq(BaseModel):
    keep_assertion_ids: list[str]
    target_count: int = 6

@router.post("/{question_id}/assertions/complete")
async def complete_assertions(question_id: str, req: CompleteAssertionsReq, db: AsyncSession = Depends(get_db)):
    q, keep = await _load_question_and_assertions(question_id, req.keep_assertion_ids, db)
    
    def serialize(a):
        return {
            "trigger": a.trigger.value if hasattr(a.trigger, "value") else a.trigger, 
            "trigger_selector": a.trigger_selector, "check_selector": a.check_selector,
            "check_type": a.check_type.value if hasattr(a.check_type, "value") else a.check_type, 
            "expected_result": a.expected_result
        }
        
    new_raw = await generate_assertions_from_llm(
        title=q.title, description=q.description_html, html=q.reference_html, css=q.reference_css, js=q.reference_js,
        keep_assertions=[serialize(a) for a in keep],
        target_count=req.target_count, mode="diversify",
    )
    return await _save_and_revalidate(q, keep, new_raw, db)


class RepairAssertionsReq(BaseModel):
    failed_assertion_ids: list[str]
    keep_assertion_ids: list[str]

@router.post("/{question_id}/assertions/repair")
async def repair_assertions(question_id: str, req: RepairAssertionsReq, db: AsyncSession = Depends(get_db)):
    q, keep = await _load_question_and_assertions(question_id, req.keep_assertion_ids, db)
    _, failed = await _load_question_and_assertions(question_id, req.failed_assertion_ids, db)
    
    def serialize(a):
        return {
            "trigger": a.trigger.value if hasattr(a.trigger, "value") else a.trigger, 
            "trigger_selector": a.trigger_selector, "check_selector": a.check_selector,
            "check_type": a.check_type.value if hasattr(a.check_type, "value") else a.check_type, 
            "expected_result": a.expected_result
        }
        
    failed_context = [{**serialize(a), "error": a.last_validation_error} for a in failed]

    new_raw = await generate_assertions_from_llm(
        title=q.title, description=q.description_html, html=q.reference_html, css=q.reference_css, js=q.reference_js,
        keep_assertions=[serialize(a) for a in keep],
        failed_context=failed_context, mode="repair",
    )
    
    # Delete the old failed rows
    from sqlalchemy import delete
    await db.execute(delete(Assertion).where(Assertion.id.in_(req.failed_assertion_ids)))
    
    return await _save_and_revalidate(q, keep, new_raw, db)
'''

text += "\n" + endpoints

with open('backend/api/v1/questions/crud.py', 'w', encoding='utf-8') as f:
    f.write(text)
