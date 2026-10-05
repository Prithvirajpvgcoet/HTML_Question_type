"""add last_validation_results to questions"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "57e53a2cc301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("last_validation_results", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("questions", "last_validation_results")
