from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.file import File
from backend.app.models.file_status import FileStatus
from backend.app.models.workspace import Workspace
from backend.app.repositories.file_repository import FileRepository
from backend.app.services.file_hash_service import calculate_sha256
from backend.app.services.file_metadata_service import (
    get_file_modified_at,
)
from backend.app.services.file_scanner import scan_directory


ProgressCallback = Callable[
    [int, int],
    None,
]


class WorkspaceScanService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.file_repository = FileRepository(session)

    def scan(
        self,
        workspace: Workspace,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, int]:
        files_found = 0
        files_indexed = 0
        new_files = 0
        unchanged_files = 0
        modified_files = 0
        duplicates = 0
        errors = 0

        existing_paths = self.file_repository.get_paths(
            workspace.id,
        )

        scanned_paths: set[str] = set()

        root = Path(workspace.root_path)

        fingerprints = (
            self.file_repository.get_fingerprints_by_size(
                workspace.id,
            )
        )

        paths = list(scan_directory(root))

        total_files = len(paths)

        print(f">>> SCAN FOUND {total_files} FILES")

        last_progress = -1

        for processed_count, path in enumerate(
                paths,
                start=1,
        ):
            print(f">>> PROCESSING {processed_count}/{total_files}: {path}")

            files_found += 1

            scanned_paths.add(str(path))

            try:
                stat = path.stat()

                size = stat.st_size
                modified_at = get_file_modified_at(path)

                existing_file = (
                    self.file_repository.get_by_path(
                        workspace_id=workspace.id,
                        path=str(path),
                    )
                )

                if existing_file is not None:
                    if (
                        existing_file.size == size
                        and existing_file.modified_at
                        == modified_at
                    ):
                        existing_file.last_scanned_at = (
                            datetime.now(timezone.utc)
                        )

                        existing_file.status = FileStatus.ACTIVE

                        unchanged_files += 1

                    else:
                        modified_files += 1

                        sha256 = calculate_sha256(path)

                        existing_file.name = path.name
                        existing_file.size = size
                        existing_file.sha256 = sha256
                        existing_file.modified_at = modified_at
                        existing_file.last_scanned_at = (
                            datetime.now(timezone.utc)
                        )
                        existing_file.status = FileStatus.ACTIVE

                        fingerprints.setdefault(
                            size,
                            set(),
                        ).add(sha256)

                else:
                    new_files += 1

                    sha256 = calculate_sha256(path)

                    existing_hashes = fingerprints.get(
                        size,
                        set(),
                    )

                    is_duplicate = (
                        sha256 in existing_hashes
                    )

                    if is_duplicate:
                        duplicates += 1
                    else:
                        files_indexed += 1

                    file = File(
                        workspace_id=workspace.id,
                        name=path.name,
                        path=str(path),
                        size=size,
                        mime_type=None,
                        extension=(
                            path.suffix.lower()
                            or None
                        ),
                        sha256=sha256,
                        modified_at=modified_at,
                        last_scanned_at=(
                            datetime.now(timezone.utc)
                        ),
                        status=FileStatus.ACTIVE,
                    )

                    self.session.add(file)

                    fingerprints.setdefault(
                        size,
                        set(),
                    ).add(sha256)

            except OSError:
                errors += 1

            progress = (
                int(
                    processed_count * 100 / total_files
                )
                if total_files > 0
                else 100
            )

            if (
                    progress != last_progress
                    and (
                    progress % 5 == 0
                    or progress == 100
            )
            ):
                print(
                    f">>> PROGRESS CALLBACK: "
                    f"{processed_count}/{total_files} = {progress}%"
                )

                if progress_callback is not None:
                    progress_callback(
                        processed_count,
                        total_files,
                    )

                last_progress = progress

        missing_paths = existing_paths - scanned_paths

        for missing_path in missing_paths:
            missing_file = (
                self.file_repository.get_by_path(
                    workspace_id=workspace.id,
                    path=missing_path,
                )
            )

            if missing_file is not None:
                missing_file.status = FileStatus.MISSING

        missing_files = len(missing_paths)

        self.session.commit()

        return {
            "files_found": files_found,
            "files_indexed": files_indexed,
            "new_files": new_files,
            "unchanged_files": unchanged_files,
            "modified_files": modified_files,
            "duplicates": duplicates,
            "missing_files": missing_files,
            "errors": errors,
        }
