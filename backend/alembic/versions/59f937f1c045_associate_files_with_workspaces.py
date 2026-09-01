"""associate files with workspaces

Revision ID: 59f937f1c045
Revises: 110a2ddd9da1
Create Date: 2026-08-28 16:54:59.762146

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "59f937f1c045"
down_revision: str | Sequence[str] | None = "110a2ddd9da1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "files",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
    )
    op.drop_index(
        op.f("ix_files_user_id"),
        table_name="files",
    )
    op.create_index(
        op.f("ix_files_workspace_id"),
        "files",
        ["workspace_id"],
        unique=False,
    )
    op.drop_constraint(
        op.f("files_user_id_fkey"),
        "files",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "files_workspace_id_fkey",
        "files",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("files", "user_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "files",
        sa.Column(
            "user_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_constraint(
        "files_workspace_id_fkey",
        "files",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "files_user_id_fkey",
        "files",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index(
        op.f("ix_files_workspace_id"),
        table_name="files",
    )
    op.create_index(
        op.f("ix_files_user_id"),
        "files",
        ["user_id"],
        unique=False,
    )
    op.drop_column("files", "workspace_id")
