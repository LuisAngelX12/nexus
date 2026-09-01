from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from collections import defaultdict

from backend.app.models.file import File


class FileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_fingerprints_by_size(
            self,
            workspace_id: UUID,
    ) -> dict[int, set[str]]:
        statement = select(
            File.size,
            File.sha256,
        ).where(
            File.workspace_id == workspace_id,
        )

        fingerprints: dict[int, set[str]] = defaultdict(set)

        for size, sha256 in self.session.execute(statement):
            fingerprints[size].add(sha256)

        return dict(fingerprints)

    def get_by_hash(
        self,
        workspace_id: UUID,
        sha256: str,
    ) -> File | None:
        statement = select(File).where(
            File.workspace_id == workspace_id,
            File.sha256 == sha256,
        )

        return self.session.scalar(statement)

    def get_by_path(
            self,
            workspace_id: UUID,
            path: str,
    ) -> File | None:
        statement = select(File).where(
            File.workspace_id == workspace_id,
            File.path == path,
        )

        return self.session.scalar(statement)

    def get_paths(
            self,
            workspace_id: UUID,
    ) -> set[str]:
        statement = select(File.path).where(
            File.workspace_id == workspace_id,
        )

        return set(self.session.scalars(statement))

    def create(self, file: File) -> File:
        self.session.add(file)
        self.session.commit()
        self.session.refresh(file)

        return file

    def get_hashes_by_size(
            self,
            workspace_id: UUID,
            size: int,
    ) -> set[str]:
        statement = select(File.sha256).where(
            File.workspace_id == workspace_id,
            File.size == size,
        )

        return set(self.session.scalars(statement))

    def exists_by_size(
        self,
        workspace_id: UUID,
        size: int,
    ) -> bool:
        statement = select(File.id).where(
            File.workspace_id == workspace_id,
            File.size == size,
        ).limit(1)

        return self.session.scalar(statement) is not None