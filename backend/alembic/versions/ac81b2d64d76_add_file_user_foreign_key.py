"""add file user foreign key

Revision ID: ac81b2d64d76
Revises: fbd52f362e6b
Create Date: 2026-08-28 11:14:55.169303

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ac81b2d64d76"
down_revision: Union[str, Sequence[str], None] = "fbd52f362e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_foreign_key(
        "files_user_id_fkey",
        "files",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "files_user_id_fkey",
        "files",
        type_="foreignkey",
    )
