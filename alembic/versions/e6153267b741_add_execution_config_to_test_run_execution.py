"""add execution_config to test_run_execution

Revision ID: e6153267b741
Revises: 0a251edfd975
Create Date: 2026-01-15 17:36:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "e6153267b741"
down_revision = "0a251edfd975"
branch_labels = None
depends_on = None


def upgrade():
    # Add execution_config column to testrunexecution table (optional JSON)
    op.add_column(
        "testrunexecution",
        sa.Column(
            "execution_config", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade():
    # Remove execution_config column
    op.drop_column("testrunexecution", "execution_config")
