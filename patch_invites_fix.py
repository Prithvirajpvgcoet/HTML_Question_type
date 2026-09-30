import os

file_path = 'backend/api/v1/invites/crud.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Revert to datetime.utcnow()
code = code.replace(
    'import datetime as dt\n        invite.started_at = dt.datetime.now(dt.timezone.utc)',
    'invite.started_at = datetime.utcnow()'
)
code = code.replace(
    'import datetime as dt\n    invite.expires_at = dt.datetime.now(dt.timezone.utc)',
    'invite.expires_at = datetime.utcnow()'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Reverted to naive utcnow for database compatibility')
