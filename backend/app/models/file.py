from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class File(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "files"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    path: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    extension: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )