"""Rename Python Testing Suite commissioning suite names

Revision ID: b1f9e3d7c2a5
Revises: a16c8c20cd36
Create Date: 2026-05-18 00:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b1f9e3d7c2a5"
down_revision = "a16c8c20cd36"
branch_labels = None
depends_on = None


def upgrade():
    # Rename "Python Testing Suite" -> "Python Testing Suite - Auto commissioning"
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - Auto commissioning' "
        "where public_id='Python Testing Suite'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - Auto commissioning', "
        "title='Python Testing Suite - Auto commissioning', "
        "description='Python Testing Suite - Auto commissioning' "
        "where public_id='Python Testing Suite'"
    )

    # Rename "Python Testing Suite - No commissioning"
    #     -> "Python Testing Suite - No auto commissioning"
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - No auto commissioning' "
        "where public_id='Python Testing Suite - No commissioning'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - No auto commissioning', "
        "title='Python Testing Suite - No auto commissioning', "
        "description='Python Testing Suite - No auto commissioning' "
        "where public_id='Python Testing Suite - No commissioning'"
    )

    # Handle custom variants (with "-custom" suffix)
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - Auto commissioning-custom' "
        "where public_id='Python Testing Suite-custom'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - Auto commissioning-custom', "
        "title='Python Testing Suite - Auto commissioning-custom', "
        "description='Python Testing Suite - Auto commissioning-custom' "
        "where public_id='Python Testing Suite-custom'"
    )
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - No auto commissioning-custom' "
        "where public_id='Python Testing Suite - No commissioning-custom'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - No auto commissioning-custom', "
        "title='Python Testing Suite - No auto commissioning-custom', "
        "description='Python Testing Suite - No auto commissioning-custom' "
        "where public_id='Python Testing Suite - No commissioning-custom'"
    )


def downgrade():
    # Revert "Python Testing Suite - Auto commissioning" -> "Python Testing Suite"
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite' "
        "where public_id='Python Testing Suite - Auto commissioning'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite', "
        "title='Python Testing Suite', "
        "description='Python Testing Suite' "
        "where public_id='Python Testing Suite - Auto commissioning'"
    )

    # Revert "Python Testing Suite - No auto commissioning"
    #     -> "Python Testing Suite - No commissioning"
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - No commissioning' "
        "where public_id='Python Testing Suite - No auto commissioning'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - No commissioning', "
        "title='Python Testing Suite - No commissioning', "
        "description='Python Testing Suite - No commissioning' "
        "where public_id='Python Testing Suite - No auto commissioning'"
    )

    # Revert custom variants
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite-custom' "
        "where public_id='Python Testing Suite - Auto commissioning-custom'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite-custom', "
        "title='Python Testing Suite-custom', "
        "description='Python Testing Suite-custom' "
        "where public_id='Python Testing Suite - Auto commissioning-custom'"
    )
    op.execute(
        "Update testsuiteexecution "
        "set public_id='Python Testing Suite - No commissioning-custom' "
        "where public_id='Python Testing Suite - No auto commissioning-custom'"
    )
    op.execute(
        "Update testsuitemetadata "
        "set public_id='Python Testing Suite - No commissioning-custom', "
        "title='Python Testing Suite - No commissioning-custom', "
        "description='Python Testing Suite - No commissioning-custom' "
        "where public_id='Python Testing Suite - No auto commissioning-custom'"
    )
