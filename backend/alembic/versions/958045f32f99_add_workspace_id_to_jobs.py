"""add workspace_id to jobs

Revision ID: 958045f32f99
Revises: 60a1957e4f4d
Create Date: 2026-08-31 20:49:15.496030

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "958045f32f99"
down_revision: str | Sequence[str] | None = "60a1957e4f4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "jobs",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
    )
    op.create_index(
        op.f("ix_jobs_workspace_id"),
        "jobs",
        ["workspace_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_jobs_workspace_id_workspaces",
        "jobs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_jobs_workspace_id_workspaces",
        "jobs",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_jobs_workspace_id"),
        table_name="jobs",
    )
    op.drop_column("jobs", "workspace_id")
