import os

file_path = 'backend/Dockerfile'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]',
    'CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched Backend Dockerfile')
