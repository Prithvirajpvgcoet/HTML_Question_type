import os

file_path = 'backend/db/migrations/env.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'url = settings.database_url_sync or config.get_main_option("sqlalchemy.url")',
    'url = settings.database_url_sync or config.get_main_option("sqlalchemy.url")\n    if url and url.startswith("postgresql://"):\n        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched env.py')
