from datetime import datetime
from enum import StrEnum
from uuid import UUID
from sqlalchemy import ForeignKey, DateTime

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    WORKSPACE_SCAN = "workspace_scan"


class Job(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[JobType] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[JobStatus] = mapped_column(
        String(20),
        nullable=False,
        default=JobStatus.QUEUED,
        index=True,
    )

    progress: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    total_files: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    files_found: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    files_processed: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    duplicates: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )