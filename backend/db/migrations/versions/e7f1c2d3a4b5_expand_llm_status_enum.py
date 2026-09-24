"""Expand LLMStatus enum for BUG-5: add skipped_playwright_passed, verified_pass, verified_fail, error, not_run

Revision ID: e7f1c2d3a4b5
Revises: d412bdb7a37a
Create Date: 2026-09-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'e7f1c2d3a4b5'
down_revision = 'd412bdb7a37a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires ALTER TYPE ... ADD VALUE for enum expansion
    op.execute("ALTER TYPE llmstatus ADD VALUE IF NOT EXISTS 'skipped_playwright_passed'")
    op.execute("ALTER TYPE llmstatus ADD VALUE IF NOT EXISTS 'verified_pass'")
    op.execute("ALTER TYPE llmstatus ADD VALUE IF NOT EXISTS 'verified_fail'")
    op.execute("ALTER TYPE llmstatus ADD VALUE IF NOT EXISTS 'error'")
    op.execute("ALTER TYPE llmstatus ADD VALUE IF NOT EXISTS 'not_run'")
    # Migrate old values to new ones
    op.execute("""
        UPDATE evaluation_results
        SET llm_status = 'skipped_playwright_passed'
        WHERE llm_status = 'passed'
    """)
    op.execute("""
        UPDATE evaluation_results
        SET llm_status = 'verified_fail'
        WHERE llm_status = 'failed'
    """)
    op.execute("""
        UPDATE evaluation_results
        SET llm_status = 'not_run'
        WHERE llm_status = 'not_evaluated'
    """)


def downgrade() -> None:
    # Revert data values back to old enum strings
    op.execute("""
        UPDATE evaluation_results
        SET llm_status = 'passed'
        WHERE llm_status = 'skipped_playwright_passed'
    """)
    op.execute("""
        UPDATE evaluation_results
        SET llm_status = 'passed'
        WHERE llm_status = 'verified_pass'
    """)
    op.execute("""
        UPDATE evaluation_results
        SET llm_status = 'failed'
        WHERE llm_status = 'verified_fail'
    """)
    op.execute("""
        UPDATE evaluation_results
        SET llm_status = 'not_evaluated'
        WHERE llm_status IN ('not_run', 'error')
    """)
    # Note: PostgreSQL does not support REMOVE VALUE from enum;
    # a full type recreation is needed to fully roll back the enum shape.
