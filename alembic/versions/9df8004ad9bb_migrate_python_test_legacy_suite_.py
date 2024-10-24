"""Migrate python test legacy suite executions

Revision ID: 9df8004ad9bb
Revises: 96ee37627a48
Create Date: 2024-04-24 17:26:26.770729

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "9df8004ad9bb"
down_revision = "96ee37627a48"
branch_labels = None
depends_on = None


def upgrade():
    # Update Python Testing Suite - Legacy suite reference
    # to Python Testing Suite - Old script format
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - Old script format' "
        "where public_id='Python Testing Suite - Legacy'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - Old script format', "
        "title='Python Testing Suite - Old script format', "
        "description='Python Testing Suite - Old script format' "
        "where public_id='Python Testing Suite - Legacy'"
    )


def downgrade():
    # Update Python Testing Suite - Old script format suite reference
    # to Python Testing Suite - Legacy
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - Legacy' "
        "where public_id='Python Testing Suite - Old script format'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - Legacy', "
        "title='Python Testing Suite - Legacy', "
        "description='Python Testing Suite - Legacy' "
        "where public_id='Python Testing Suite - Old script format'"
    )
