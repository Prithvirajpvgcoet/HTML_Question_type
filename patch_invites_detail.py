import os

file_path = 'backend/api/v1/invites/crud.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'if invite.used_at is not None or invite.expires_at < datetime.utcnow():\n        raise HTTPException(status_code=400, detail="Invite invalid or expired")',
    'if invite.used_at is not None:\n        raise HTTPException(status_code=400, detail="Test already completed")\n    if invite.expires_at < datetime.utcnow():\n        raise HTTPException(status_code=400, detail="Invite expired")'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched backend invite details')
