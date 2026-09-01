from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.file import File
from backend.app.repositories.file_repository import FileRepository
from backend.app.services.file_hash_service import calculate_sha256


class DuplicateFileError(Exception):
    def __init__(self, existing_file: File) -> None:
        self.existing_file = existing_file
        super().__init__(f"Duplicate file detected: {existing_file.name}")


class FileService:
    def __init__(self, session: Session) -> None:
        self.repository = FileRepository(session)

    def index_file(
        self,
        workspace_id: UUID,
        file_path: Path,
        mime_type: str | None = None,
    ) -> File:
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        if not file_path.is_file():
            raise ValueError("Path does not point to a file.")

        sha256 = calculate_sha256(file_path)

        existing_file = self.repository.get_by_hash(
            workspace_id=workspace_id,
            sha256=sha256,
        )

        if existing_file is not None:
            raise DuplicateFileError(existing_file)

        file = File(
            workspace_id=workspace_id,
            name=file_path.name,
            path=str(file_path),
            size=file_path.stat().st_size,
            mime_type=mime_type,
            extension=file_path.suffix.lower() or None,
            sha256=sha256,
        )

        return self.repository.create(file)
