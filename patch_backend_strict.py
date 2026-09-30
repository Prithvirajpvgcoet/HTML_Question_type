import os
import re

file_path = 'backend/api/v1/submissions/crud.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Make invite consumption atomic
old_invite = '''    if req.token:
        from models import CandidateInvite
        from datetime import datetime
        res = await db.execute(select(CandidateInvite).where(CandidateInvite.token == req.token))
        invite = res.scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=400, detail="Invalid token")
        if invite.used_at:
            raise HTTPException(status_code=400, detail="Invite already used. You can only submit once.")
        invite.used_at = datetime.utcnow()'''

new_invite = '''    if req.token:
        from models import CandidateInvite
        from datetime import datetime
        from sqlalchemy import update
        res = await db.execute(
            update(CandidateInvite)
            .where(CandidateInvite.token == req.token, CandidateInvite.used_at.is_(None))
            .values(used_at=datetime.utcnow())
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=400, detail="Invite already used or invalid.")'''
code = code.replace(old_invite, new_invite)

# Reject empty submissions
if "Empty submission" not in code:
    code = code.replace(
        'from models.question import Question',
        'if not (req.submitted_html or req.submitted_css or req.submitted_js).strip():\n        raise HTTPException(status_code=400, detail="Empty submission")\n\n    from models.question import Question'
    )

# Make evaluation idempotent
old_eval = '''    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    background_tasks.add_task(process_evaluation_task, submission_id)'''

new_eval = '''    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if sub.status != SubmissionStatus.pending:
        return {"message": "Already queued", "submission_id": submission_id}
    sub.status = SubmissionStatus.queued
    await db.commit()

    background_tasks.add_task(process_evaluation_task, submission_id)'''
code = code.replace(old_eval, new_eval)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched backend strictness')
