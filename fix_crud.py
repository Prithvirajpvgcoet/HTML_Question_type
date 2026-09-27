import re

with open('backend/api/v1/questions/crud.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace _validate_against_reference
old_validate = '''async def _validate_against_reference(
    q: Question,
    saved_assertions: list,
    db: AsyncSession
) -> None:
    \"\"\"
    Runs saved_assertions against q's reference solution via the Playwright evaluator.
    
    If all assertions pass  — marks q.validation_status = passed and commits.
    If any assertion fails  — raises HTTPException 400 with structured failure details.
    
    This is the ground-truth gate: a correct reference solution must always pass
    its own generated assertions. Any failure here means the assertions are wrong,
    not the reference code.
    \"\"\"
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

    # If we got here, the reference code failed its own generated tests!
    q.validation_status = ValidationStatus.failed
    await db.commit()

    logger.warning(
        "reference_validation_failed",
        extra={"question_id": q.id, "failed_count": len(failed), "failures": failed}
    )

    raise HTTPException(
        status_code=400,
        detail={
            "message": f"{len(failed)} of {len(saved_assertions)} assertions fail against your own reference solution. This means the assertions are incomplete or wrong — not the reference code. Regenerate assertions to fix.",
            "failed_assertions": failed
        }
    )'''

new_validate = '''async def _validate_against_reference(
    q: Question,
    saved_assertions: list,
    db: AsyncSession
) -> dict:
    results = await evaluate_submission(
        html=q.reference_html or "",
        css=q.reference_css or "",
        js=q.reference_js or "",
        assertions=saved_assertions
    )
    results_by_id = {r["assertion_id"]: r for r in results}

    passed, failed = [], []
    for a in saved_assertions:
        r = results_by_id.get(a.id)
        if r and r["passed"]:
            a.last_validation_status = "passed"
            a.last_validation_error = None
            passed.append(a)
        else:
            a.last_validation_status = "failed"
            a.last_validation_error = (r or {}).get("error", "")
            failed.append(a)

    q.validation_status = ValidationStatus.passed if not failed else ValidationStatus.failed
    q.last_validation_results = json.dumps(results)
    await db.commit()
    for a in saved_assertions:
        await db.refresh(a)

    return {"passed": passed, "failed": failed}'''

text = text.replace(old_validate, new_validate)

# Update generate_assertions
old_gen = '''    # 5. Phase 2: Ground-truth reference validation
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
    }'''

new_gen = '''    # 5. Phase 2: Ground-truth reference validation
    split = await _validate_against_reference(q, saved_assertions, db)
    
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
        "message": "Generated",
        "passed_count": len(split["passed"]),
        "failed_count": len(split["failed"]),
        "assertions": [serialize(a) for a in saved_assertions],
    }'''

text = text.replace(old_gen, new_gen)

with open('backend/api/v1/questions/crud.py', 'w', encoding='utf-8') as f:
    f.write(text)
