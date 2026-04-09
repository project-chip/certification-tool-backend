"""add execution_pics to test_run_execution

Revision ID: a16c8c20cd36
Revises: e6153267b741
Create Date: 2026-04-08 17:41:21.198510

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "a16c8c20cd36"
down_revision = "e6153267b741"
branch_labels = None
depends_on = None


def upgrade():
    # Add execution_pics column to testrunexecution table (optional JSON)
    op.add_column(
        "testrunexecution",
        sa.Column(
            "execution_pics", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade():
    # Remove execution_pics column
    op.drop_column("testrunexecution", "execution_pics")
