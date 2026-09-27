import re

with open('backend/db/migrations/versions/f0bf4f116a03_add_assertion_validation_tracking.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('nullable=False', "nullable=False, server_default='not_run'")

with open('backend/db/migrations/versions/f0bf4f116a03_add_assertion_validation_tracking.py', 'w', encoding='utf-8') as f:
    f.write(text)
