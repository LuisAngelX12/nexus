from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.file import File
from backend.app.models.workspace import Workspace
from backend.app.repositories.file_repository import FileRepository
from backend.app.services.file_hash_service import calculate_sha256
from backend.app.services.file_scanner import scan_directory
from backend.app.services.file_service import DuplicateFileError


class WorkspaceScanService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.file_repository = FileRepository(session)

    def scan(
        self,
        workspace: Workspace,
    ) -> dict[str, int]:
        files_found = 0
        files_indexed = 0
        duplicates = 0
        errors = 0

        root = Path(workspace.root_path)

        for path in scan_directory(root):
            files_found += 1

            try:
                sha256 = calculate_sha256(path)

                existing_file = self.file_repository.get_by_hash(
                    user_id=workspace.user_id,
                    sha256=sha256,
                )

                if existing_file is not None:
                    duplicates += 1
                    continue

                file = File(
                    user_id=workspace.user_id,
                    name=path.name,
                    path=str(path),
                    size=path.stat().st_size,
                    mime_type=None,
                    extension=path.suffix.lower() or None,
                    sha256=sha256,
                )

                self.file_repository.create(file)
                files_indexed += 1

            except (OSError, ValueError):
                errors += 1

        return {
            "files_found": files_found,
            "files_indexed": files_indexed,
            "duplicates": duplicates,
            "errors": errors,
        }