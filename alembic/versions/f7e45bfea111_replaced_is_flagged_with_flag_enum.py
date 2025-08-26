"""Replaced is_flagged with flag enum

Revision ID: f7e45bfea111
Revises: 0271e52e936d
Create Date: 2025-07-25 10:34:21.603892
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f7e45bfea111"
down_revision: Union[str, Sequence[str], None] = "0271e52e936d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the enum type to create
callflag_enum = sa.Enum("NORMAL", "CONCERN", "FATAL", name="callflag")


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Create enum type
    callflag_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: Add columns using the enum
    op.add_column(
        "audit_reports",
        sa.Column("flag", callflag_enum, nullable=False, server_default="NORMAL"),
    )
    op.drop_column("audit_reports", "is_flagged")

    op.add_column(
        "calls",
        sa.Column("flag", callflag_enum, nullable=False, server_default="NORMAL"),
    )
    op.drop_column("calls", "is_flagged")


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Revert columns
    op.add_column("calls", sa.Column("is_flagged", sa.Boolean(), nullable=True))
    op.drop_column("calls", "flag")

    op.add_column("audit_reports", sa.Column("is_flagged", sa.Boolean(), nullable=True))
    op.drop_column("audit_reports", "flag")

    # Step 2: Drop the enum type
    callflag_enum.drop(op.get_bind(), checkfirst=True)
