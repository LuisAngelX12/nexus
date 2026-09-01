import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
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

logger = logging.getLogger(__name__)

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
        start_time = time.perf_counter()

        files_found = 0
        files_indexed = 0
        new_files = 0
        unchanged_files = 0
        modified_files = 0
        duplicates = 0
        skipped_files = 0
        permission_errors = 0
        errors = 0

        existing_paths = self.file_repository.get_paths(
            workspace.id,
        )

        scanned_paths: set[str] = set()

        root = Path(workspace.root_path)

        fingerprints = self.file_repository.get_fingerprints_by_size(
            workspace.id,
        )

        paths = list(scan_directory(root))

        total_files = len(paths)

        logger.info(
            "scan_files_found total_files=%s workspace_id=%s",
            total_files,
            workspace.id,
        )

        last_progress = -1

        for processed_count, path in enumerate(
            paths,
            start=1,
        ):
            logger.debug(
                "scan_processing file=%s progress=%s/%s",
                path,
                processed_count,
                total_files,
            )

            files_found += 1

            scanned_paths.add(str(path))

            try:
                stat = path.stat()

                size = stat.st_size
                modified_at = get_file_modified_at(path)

                existing_file = self.file_repository.get_by_path(
                    workspace_id=workspace.id,
                    path=str(path),
                )

                if existing_file is not None:
                    if existing_file.size == size and existing_file.modified_at == modified_at:
                        existing_file.last_scanned_at = datetime.now(UTC)

                        existing_file.status = FileStatus.ACTIVE

                        unchanged_files += 1

                    else:
                        modified_files += 1

                        sha256 = calculate_sha256(path)

                        existing_file.name = path.name
                        existing_file.size = size
                        existing_file.sha256 = sha256
                        existing_file.modified_at = modified_at
                        existing_file.last_scanned_at = datetime.now(UTC)
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

                    is_duplicate = sha256 in existing_hashes

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
                        extension=(path.suffix.lower() or None),
                        sha256=sha256,
                        modified_at=modified_at,
                        last_scanned_at=(datetime.now(UTC)),
                        status=FileStatus.ACTIVE,
                    )

                    self.session.add(file)

                    fingerprints.setdefault(
                        size,
                        set(),
                    ).add(sha256)

            except PermissionError:
                skipped_files += 1
                permission_errors += 1

                logger.warning(
                    "file_skipped path=%s reason=permission_denied",
                    path,
                )

                continue

            except OSError as exc:
                errors += 1
                skipped_files += 1

                logger.warning(
                    "file_skipped path=%s reason=%s",
                    path,
                    exc,
                )

                continue

            progress = int(processed_count * 100 / total_files) if total_files > 0 else 100

            if progress != last_progress and (progress % 5 == 0 or progress == 100):
                logger.info(
                    "scan_progress workspace_id=%s progress=%s%% processed=%s total=%s",
                    workspace.id,
                    progress,
                    processed_count,
                    total_files,
                )

                if progress_callback is not None:
                    progress_callback(
                        processed_count,
                        total_files,
                    )

                last_progress = progress

        missing_paths = existing_paths - scanned_paths

        for missing_path in missing_paths:
            missing_file = self.file_repository.get_by_path(
                workspace_id=workspace.id,
                path=missing_path,
            )

            if missing_file is not None:
                missing_file.status = FileStatus.MISSING

        missing_files = len(missing_paths)

        duration = time.perf_counter() - start_time

        processed = total_files

        files_per_second = processed / duration if duration > 0 else 0

        logger.info(
            "scan_performance job_id=%s files=%s duration_seconds=%.2f files_per_second=%.2f",
            workspace.id,
            processed,
            duration,
            files_per_second,
        )

        self.session.commit()

        return {
            "files_found": files_found,
            "files_indexed": files_indexed,
            "new_files": new_files,
            "unchanged_files": unchanged_files,
            "modified_files": modified_files,
            "duplicates": duplicates,
            "missing_files": missing_files,
            "skipped_files": skipped_files,
            "permission_errors": permission_errors,
            "errors": errors,
        }
