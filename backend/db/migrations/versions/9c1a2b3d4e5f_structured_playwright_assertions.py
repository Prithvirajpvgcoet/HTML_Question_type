"""replace free-text assertions with the structured Playwright contract

Revision ID: 9c1a2b3d4e5f
Revises: 78fda130c991
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9c1a2b3d4e5f"
down_revision: Union[str, Sequence[str], None] = "78fda130c991"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE triggertype ADD VALUE IF NOT EXISTS 'call_function'")
        op.execute("ALTER TYPE checktype ADD VALUE IF NOT EXISTS 'dom_absence'")
        op.execute("ALTER TYPE checktype ADD VALUE IF NOT EXISTS 'element_count'")
        op.execute("ALTER TYPE checktype ADD VALUE IF NOT EXISTS 'function_presence'")
        op.execute("ALTER TYPE tcstatus ADD VALUE IF NOT EXISTS 'skipped'")

    assertion_operator = postgresql.ENUM(
        "equals", "contains", "regex", "exists", "not_exists",
        name="assertionoperator",
    )
    assertion_operator.create(op.get_bind(), checkfirst=True)
    op.add_column("assertions", sa.Column("property_name", sa.String(length=200), nullable=True))
    op.add_column(
        "assertions",
        sa.Column("operator", assertion_operator, nullable=False, server_default="equals"),
    )
    op.add_column("assertions", sa.Column("expected_value", sa.Text(), nullable=True))
    op.add_column("assertions", sa.Column("input_value", sa.Text(), nullable=True))
    op.drop_column("assertions", "expected_result")
    op.add_column("evaluation_results", sa.Column("evidence_text", sa.Text(), nullable=True))
    op.add_column("evaluation_results", sa.Column("blocked_by_assertion_id", sa.String(), nullable=True))
    op.drop_column("evaluation_results", "llm_evidence_text")
    op.drop_column("evaluation_results", "llm_status")
    op.drop_column("submissions", "llm_status")
    op.drop_column("submissions", "llm_passed")
    op.drop_column("submissions", "llm_total")


def downgrade() -> None:
    llm_status = postgresql.ENUM(name="llmstatus", create_type=False)
    submission_llm_status = postgresql.ENUM(name="submissionllmstatus", create_type=False)
    op.add_column("submissions", sa.Column("llm_total", sa.Integer(), nullable=False, server_default="50"))
    op.add_column("submissions", sa.Column("llm_passed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("submissions", sa.Column("llm_status", submission_llm_status, nullable=True))
    op.add_column("evaluation_results", sa.Column("llm_status", llm_status, nullable=False, server_default="not_run"))
    op.add_column("evaluation_results", sa.Column("llm_evidence_text", sa.Text(), nullable=True))
    op.drop_column("evaluation_results", "blocked_by_assertion_id")
    op.drop_column("evaluation_results", "evidence_text")
    op.add_column(
        "assertions",
        sa.Column("expected_result", sa.Text(), nullable=False, server_default=""),
    )
    op.drop_column("assertions", "input_value")
    op.drop_column("assertions", "expected_value")
    op.drop_column("assertions", "operator")
    postgresql.ENUM(name="assertionoperator").drop(op.get_bind(), checkfirst=True)
    # PostgreSQL enum values are intentionally retained; removing them requires
    # rebuilding each enum and can invalidate historical rows.
