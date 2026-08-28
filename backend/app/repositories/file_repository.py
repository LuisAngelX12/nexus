from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.file import File


class FileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_hash(
        self,
        user_id: UUID,
        sha256: str,
    ) -> File | None:
        statement = select(File).where(
            File.user_id == user_id,
            File.sha256 == sha256,
        )

        return self.session.scalar(statement)

    def create(self, file: File) -> File:
        self.session.add(file)
        self.session.commit()
        self.session.refresh(file)

        return file