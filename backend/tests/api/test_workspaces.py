from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from backend.app.models.file_status import FileStatus
from backend.app.services.workspace_scan_service import WorkspaceScanService


class FakePath:
    def __init__(
        self,
        path: str,
        size: int = 10,
        suffix: str = ".txt",
    ) -> None:
        self.path = path
        self._size = size
        self.suffix = suffix
        self.name = Path(path).name

    def __str__(self) -> str:
        return self.path

    def stat(self) -> MagicMock:
        return MagicMock(st_size=self._size)


def make_workspace() -> MagicMock:
    workspace = MagicMock()
    workspace.id = "workspace-1"
    workspace.root_path = "/workspace"
    return workspace


def configure_service(
    service: WorkspaceScanService,
    monkeypatch,
    paths: list[FakePath],
    *,
    existing_paths: set[str] | None = None,
    fingerprints: dict[int, set[str]] | None = None,
    existing_file: MagicMock | None = None,
    modified_at: datetime | None = None,
    sha256: str = "abc123",
) -> None:
    repository = MagicMock()

    repository.get_paths.return_value = existing_paths if existing_paths is not None else set()

    repository.get_fingerprints_by_size.return_value = (
        fingerprints if fingerprints is not None else {}
    )

    repository.get_by_path.return_value = existing_file

    service.file_repository = repository

    monkeypatch.setattr(
        "backend.app.services.workspace_scan_service.scan_directory",
        lambda root: paths,
    )

    if modified_at is not None:
        monkeypatch.setattr(
            "backend.app.services.workspace_scan_service.get_file_modified_at",
            lambda file_path: modified_at,
        )

    monkeypatch.setattr(
        "backend.app.services.workspace_scan_service.calculate_sha256",
        lambda file_path: sha256,
    )


def test_scan_new_file(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    path = FakePath(
        "/workspace/test.txt",
        size=100,
    )

    modified_at = datetime.now(UTC)

    configure_service(
        service,
        monkeypatch,
        [path],
        modified_at=modified_at,
        sha256="abc123",
    )

    session.add = MagicMock()
    session.commit = MagicMock()

    result = service.scan(workspace)

    assert result["files_found"] == 1
    assert result["files_indexed"] == 1
    assert result["new_files"] == 1
    assert result["unchanged_files"] == 0
    assert result["modified_files"] == 0
    assert result["duplicates"] == 0
    assert result["missing_files"] == 0
    assert result["skipped_files"] == 0
    assert result["permission_errors"] == 0
    assert result["errors"] == 0

    session.add.assert_called_once()
    session.commit.assert_called_once()


def test_scan_duplicate_file(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    path = FakePath(
        "/workspace/duplicate.txt",
        size=100,
    )

    configure_service(
        service,
        monkeypatch,
        [path],
        fingerprints={
            100: {"abc123"},
        },
    )

    session.add = MagicMock()
    session.commit = MagicMock()

    result = service.scan(workspace)

    assert result["files_found"] == 1
    assert result["new_files"] == 1
    assert result["files_indexed"] == 0
    assert result["duplicates"] == 1

    session.add.assert_called_once()
    session.commit.assert_called_once()


def test_scan_unchanged_file(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    path = FakePath(
        "/workspace/test.txt",
        size=100,
    )

    modified_at = datetime.now(UTC)

    existing_file = MagicMock()
    existing_file.size = 100
    existing_file.modified_at = modified_at

    configure_service(
        service,
        monkeypatch,
        [path],
        existing_paths={str(path)},
        existing_file=existing_file,
        modified_at=modified_at,
    )

    session.commit = MagicMock()

    result = service.scan(workspace)

    assert result["files_found"] == 1
    assert result["new_files"] == 0
    assert result["unchanged_files"] == 1
    assert result["modified_files"] == 0
    assert result["duplicates"] == 0

    assert existing_file.status == FileStatus.ACTIVE
    assert existing_file.last_scanned_at is not None

    session.commit.assert_called_once()


def test_scan_modified_file(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    path = FakePath(
        "/workspace/test.txt",
        size=200,
    )

    old_modified_at = datetime(
        2025,
        1,
        1,
        tzinfo=UTC,
    )

    new_modified_at = datetime(
        2026,
        1,
        1,
        tzinfo=UTC,
    )

    existing_file = MagicMock()
    existing_file.size = 100
    existing_file.modified_at = old_modified_at

    fingerprints: dict[int, set[str]] = {}

    configure_service(
        service,
        monkeypatch,
        [path],
        existing_paths={str(path)},
        fingerprints=fingerprints,
        existing_file=existing_file,
        modified_at=new_modified_at,
        sha256="new-hash",
    )

    session.commit = MagicMock()

    result = service.scan(workspace)

    assert result["files_found"] == 1
    assert result["new_files"] == 0
    assert result["unchanged_files"] == 0
    assert result["modified_files"] == 1

    assert existing_file.name == "test.txt"
    assert existing_file.size == 200
    assert existing_file.sha256 == "new-hash"
    assert existing_file.modified_at == new_modified_at
    assert existing_file.status == FileStatus.ACTIVE
    assert existing_file.last_scanned_at is not None

    assert fingerprints[200] == {"new-hash"}

    session.commit.assert_called_once()


def test_scan_permission_error(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    path = FakePath(
        "/workspace/protected.txt",
    )

    service.file_repository = MagicMock()
    service.file_repository.get_paths.return_value = set()
    service.file_repository.get_fingerprints_by_size.return_value = {}

    monkeypatch.setattr(
        "backend.app.services.workspace_scan_service.scan_directory",
        lambda _: [path],
    )

    def raise_permission_error(_):
        raise PermissionError("Access denied")

    monkeypatch.setattr(
        "backend.app.services.workspace_scan_service.get_file_modified_at",
        raise_permission_error,
    )

    session.commit = MagicMock()

    result = service.scan(workspace)

    assert result["files_found"] == 1
    assert result["skipped_files"] == 1
    assert result["permission_errors"] == 1
    assert result["errors"] == 0

    session.commit.assert_called_once()


def test_scan_os_error(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    path = FakePath(
        "/workspace/broken.txt",
    )

    repository = MagicMock()
    repository.get_paths.return_value = set()
    repository.get_fingerprints_by_size.return_value = {}
    repository.get_by_path.return_value = None

    service.file_repository = repository

    monkeypatch.setattr(
        "backend.app.services.workspace_scan_service.scan_directory",
        lambda _: [path],
    )

    def raise_os_error():
        raise OSError("File unavailable")

    path.stat = raise_os_error

    result = service.scan(workspace)

    assert result["files_found"] == 1
    assert result["skipped_files"] == 1
    assert result["permission_errors"] == 0
    assert result["errors"] == 1

    repository.get_paths.assert_called_once_with(
        workspace.id,
    )

    repository.get_fingerprints_by_size.assert_called_once_with(
        workspace.id,
    )

    repository.get_by_path.assert_not_called()


def test_scan_marks_missing_files(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    missing_path = "/workspace/deleted.txt"
    missing_file = MagicMock()

    service.file_repository = MagicMock()
    service.file_repository.get_paths.return_value = {
        missing_path,
    }
    service.file_repository.get_fingerprints_by_size.return_value = {}
    service.file_repository.get_by_path.return_value = missing_file

    monkeypatch.setattr(
        "backend.app.services.workspace_scan_service.scan_directory",
        lambda _: [],
    )

    session.commit = MagicMock()

    result = service.scan(workspace)

    assert result["files_found"] == 0
    assert result["missing_files"] == 1

    assert missing_file.status == FileStatus.MISSING

    session.commit.assert_called_once()


def test_scan_missing_path_without_file(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    missing_path = "/workspace/deleted.txt"

    service.file_repository = MagicMock()
    service.file_repository.get_paths.return_value = {
        missing_path,
    }
    service.file_repository.get_fingerprints_by_size.return_value = {}
    service.file_repository.get_by_path.return_value = None

    monkeypatch.setattr(
        "backend.app.services.workspace_scan_service.scan_directory",
        lambda _: [],
    )

    session.commit = MagicMock()

    result = service.scan(workspace)

    assert result["files_found"] == 0
    assert result["missing_files"] == 1

    session.commit.assert_called_once()


def test_scan_calls_progress_callback(session, monkeypatch):
    service = WorkspaceScanService(session)
    workspace = make_workspace()

    path = FakePath(
        "/workspace/test.txt",
    )

    configure_service(
        service,
        monkeypatch,
        [path],
    )

    session.add = MagicMock()
    session.commit = MagicMock()

    progress_callback = MagicMock()

    result = service.scan(
        workspace,
        progress_callback=progress_callback,
    )

    assert result["files_found"] == 1

    progress_callback.assert_called_once_with(
        1,
        1,
    )
