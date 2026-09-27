import re

with open('backend/models/assertion.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add last_validation_status and last_validation_error to Assertion model
if 'last_validation_status' not in text:
    text = text.replace('created_at: Mapped[datetime]', 'last_validation_status: Mapped[str] = mapped_column(String(20), default="not_run")\n    last_validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)\n    created_at: Mapped[datetime]')
    with open('backend/models/assertion.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Added columns to model.")
else:
    print("Columns already exist in model.")
