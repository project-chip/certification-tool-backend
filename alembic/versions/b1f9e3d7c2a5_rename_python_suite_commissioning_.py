"""Rename Python Testing Suite commissioning suite names

Revision ID: b1f9e3d7c2a5
Revises: a16c8c20cd36
Create Date: 2026-05-18 00:00:00.000000

"""
# flake8: noqa
# Ignore flake8 check for this file

from alembic import op


# revision identifiers, used by Alembic.
revision = "b1f9e3d7c2a5"
down_revision = "a16c8c20cd36"
branch_labels = None
depends_on = None


def upgrade():
    renames = {
        "Python Testing Suite": "Python Testing Suite - Auto commissioning",
        "Python Testing Suite - No commissioning": "Python Testing Suite - No auto commissioning",
        "Python Testing Suite-custom": "Python Testing Suite - Auto commissioning-custom",
        "Python Testing Suite - No commissioning-custom": "Python Testing Suite - No auto commissioning-custom",
    }

    for old_id, new_id in renames.items():
        # Update metadata first to satisfy potential foreign key constraints
        op.execute(
            f"UPDATE testsuitemetadata "
            f"SET public_id='{new_id}', title='{new_id}', description='{new_id}' "
            f"WHERE public_id='{old_id}'"
        )
        op.execute(
            f"UPDATE testsuiteexecution "
            f"SET public_id='{new_id}' "
            f"WHERE public_id='{old_id}'"
        )


def downgrade():
    renames = {
        "Python Testing Suite - Auto commissioning": "Python Testing Suite",
        "Python Testing Suite - No auto commissioning": "Python Testing Suite - No commissioning",
        "Python Testing Suite - Auto commissioning-custom": "Python Testing Suite-custom",
        "Python Testing Suite - No auto commissioning-custom": "Python Testing Suite - No commissioning-custom",
    }

    for old_id, new_id in renames.items():
        # Update metadata first to satisfy potential foreign key constraints
        op.execute(
            f"UPDATE testsuitemetadata "
            f"SET public_id='{new_id}', title='{new_id}', description='{new_id}' "
            f"WHERE public_id='{old_id}'"
        )
        op.execute(
            f"UPDATE testsuiteexecution "
            f"SET public_id='{new_id}' "
            f"WHERE public_id='{old_id}'"
        )
