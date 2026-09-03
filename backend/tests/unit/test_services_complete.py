from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.file import File
from backend.app.schemas.user import UserCreate
from backend.app.schemas.workspace import WorkspaceCreate
from backend.app.services.file_scanner import scan_directory
from backend.app.services.file_service import (
    DuplicateFileError,
    FileService,
)
from backend.app.services.path_security_service import (
    PathSecurityError,
    PathSecurityService,
)
from backend.app.services.user_service import UserAlreadyExistsError, UserService
from backend.app.services.workspace_service import WorkspaceService


def test_scan_directory_rejects_missing_root(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        list(scan_directory(missing))


def test_scan_directory_rejects_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("NEXUS", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="not a directory",
    ):
        list(scan_directory(file_path))


def test_scan_directory_returns_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    nested = root / "nested"

    nested.mkdir(parents=True)

    first = root / "one.txt"
    second = nested / "two.txt"

    first.write_text("ONE", encoding="utf-8")
    second.write_text("TWO", encoding="utf-8")

    result = set(scan_directory(root))

    assert result == {
        first.resolve(),
        second.resolve(),
    }


def test_file_service_rejects_missing_file(
    tmp_path: Path,
) -> None:
    service = FileService(MagicMock())

    missing = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        service.index_file(
            workspace_id=uuid4(),
            file_path=missing,
        )


def test_file_service_rejects_directory(
    tmp_path: Path,
) -> None:
    service = FileService(MagicMock())

    with pytest.raises(
        ValueError,
        match="does not point to a file",
    ):
        service.index_file(
            workspace_id=uuid4(),
            file_path=tmp_path,
        )


def test_file_service_rejects_duplicate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "test.txt"
    file_path.write_text("NEXUS", encoding="utf-8")

    existing_file = MagicMock(spec=File)
    existing_file.name = "existing.txt"

    repository = MagicMock()
    repository.get_by_hash.return_value = existing_file

    monkeypatch.setattr(
        "backend.app.services.file_service.FileRepository",
        lambda session: repository,
    )

    service = FileService(MagicMock())

    with pytest.raises(DuplicateFileError) as exc_info:
        service.index_file(
            workspace_id=uuid4(),
            file_path=file_path,
        )

    assert exc_info.value.existing_file is existing_file


def test_file_service_creates_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "TEST.TXT"
    file_path.write_text("NEXUS", encoding="utf-8")

    repository = MagicMock()

    def create(file: File) -> File:
        return file

    repository.get_by_hash.return_value = None
    repository.create.side_effect = create

    monkeypatch.setattr(
        "backend.app.services.file_service.FileRepository",
        lambda session: repository,
    )

    service = FileService(MagicMock())

    workspace_id = uuid4()

    result = service.index_file(
        workspace_id=workspace_id,
        file_path=file_path,
        mime_type="text/plain",
    )

    assert result.workspace_id == workspace_id
    assert result.name == "TEST.TXT"
    assert result.path == str(file_path)
    assert result.size == file_path.stat().st_size
    assert result.mime_type == "text/plain"
    assert result.extension == ".txt"
    assert result.sha256

    repository.create.assert_called_once()


def test_path_security_normalize_valid(
    tmp_path: Path,
) -> None:
    service = PathSecurityService()

    result = service.normalize(str(tmp_path))

    assert result == tmp_path.resolve()


def test_path_security_normalize_relative() -> None:
    service = PathSecurityService()

    with pytest.raises(
        PathSecurityError,
        match="absolute",
    ):
        service.normalize("relative/path")


def test_path_security_normalize_missing(
    tmp_path: Path,
) -> None:
    service = PathSecurityService()

    with pytest.raises(
        PathSecurityError,
        match="does not exist",
    ):
        service.normalize(str(tmp_path / "missing"))


def test_path_security_is_protected_exact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()

    monkeypatch.setattr(
        "backend.app.services.path_security_service.get_protected_paths",
        lambda: (protected.resolve(),),
    )

    service = PathSecurityService()

    assert service.is_protected(protected.resolve())


def test_path_security_is_protected_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protected = tmp_path / "protected"
    child = protected / "child"

    child.mkdir(parents=True)

    monkeypatch.setattr(
        "backend.app.services.path_security_service.get_protected_paths",
        lambda: (protected.resolve(),),
    )

    service = PathSecurityService()

    assert service.is_protected(child.resolve())


def test_path_security_is_not_protected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protected = tmp_path / "protected"
    other = tmp_path / "other"

    protected.mkdir()
    other.mkdir()

    monkeypatch.setattr(
        "backend.app.services.path_security_service.get_protected_paths",
        lambda: (protected.resolve(),),
    )

    service = PathSecurityService()

    assert not service.is_protected(other.resolve())


def test_path_security_validate_protected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()

    monkeypatch.setattr(
        "backend.app.services.path_security_service.get_protected_paths",
        lambda: (protected.resolve(),),
    )

    service = PathSecurityService()

    with pytest.raises(
        PathSecurityError,
        match="protected",
    ):
        service.validate(str(protected))


def test_path_security_validate_file_success(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    file_path = workspace / "file.txt"
    file_path.write_text("NEXUS", encoding="utf-8")

    service = PathSecurityService()

    result = service.validate_file(
        file_path,
        workspace,
    )

    assert result == file_path.resolve()


def test_path_security_validate_file_rejects_directory(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    service = PathSecurityService()

    with pytest.raises(
        PathSecurityError,
        match="not a file",
    ):
        service.validate_file(
            workspace,
            workspace,
        )


def test_path_security_validate_file_rejects_missing(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    service = PathSecurityService()

    with pytest.raises(FileNotFoundError):
        service.validate_file(
            workspace / "missing.txt",
            workspace,
        )


def test_user_service_authenticate_missing_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MagicMock()
    repository.get_by_email.return_value = None

    monkeypatch.setattr(
        "backend.app.services.user_service.UserRepository",
        lambda session: repository,
    )

    service = UserService(MagicMock())

    result = service.authenticate_user(
        email="TEST@example.com",
        password="password",
    )

    assert result is None

    repository.get_by_email.assert_called_once_with(
        "test@example.com",
    )


def test_user_service_authenticate_inactive_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = MagicMock()
    user.is_active = False

    repository = MagicMock()
    repository.get_by_email.return_value = user

    monkeypatch.setattr(
        "backend.app.services.user_service.UserRepository",
        lambda session: repository,
    )

    service = UserService(MagicMock())

    result = service.authenticate_user(
        email="test@example.com",
        password="password",
    )

    assert result is None


def test_user_service_create_existing_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MagicMock()
    repository.get_by_email.return_value = MagicMock()

    monkeypatch.setattr(
        "backend.app.services.user_service.UserRepository",
        lambda session: repository,
    )

    service = UserService(MagicMock())

    data = UserCreate(
        email="test@example.com",
        password="password",
        first_name="Test",
        last_name="User",
    )

    with pytest.raises(
        UserAlreadyExistsError,
        match="already exists",
    ):
        service.create_user(data)


def test_user_service_create_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MagicMock()
    repository.get_by_email.return_value = None
    repository.create.side_effect = IntegrityError(
        "duplicate",
        {},
        Exception("duplicate"),
    )

    monkeypatch.setattr(
        "backend.app.services.user_service.UserRepository",
        lambda session: repository,
    )

    service = UserService(MagicMock())

    data = UserCreate(
        email="TEST@example.com",
        password="password",
        first_name=" Test ",
        last_name=" User ",
    )

    with pytest.raises(
        UserAlreadyExistsError,
        match="already exists",
    ):
        service.create_user(data)


def test_workspace_service_missing_directory(
    tmp_path: Path,
) -> None:
    repository = MagicMock()

    service = WorkspaceService(MagicMock())
    service.repository = repository

    data = WorkspaceCreate(
        name="Test",
        root_path=str(tmp_path / "missing"),
    )

    with pytest.raises(FileNotFoundError):
        service.create_workspace(
            user_id=uuid4(),
            data=data,
        )


def test_workspace_service_rejects_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("NEXUS", encoding="utf-8")

    service = WorkspaceService(MagicMock())

    data = WorkspaceCreate(
        name="Test",
        root_path=str(file_path),
    )

    with pytest.raises(
        ValueError,
        match="must be a directory",
    ):
        service.create_workspace(
            user_id=uuid4(),
            data=data,
        )


def test_workspace_service_creates_workspace(
    tmp_path: Path,
) -> None:
    repository = MagicMock()

    def create(workspace):
        return workspace

    repository.create.side_effect = create

    service = WorkspaceService(MagicMock())
    service.repository = repository

    user_id = uuid4()

    data = WorkspaceCreate(
        name="  My Workspace  ",
        root_path=str(tmp_path),
    )

    result = service.create_workspace(
        user_id=user_id,
        data=data,
    )

    assert result.user_id == user_id
    assert result.name == "My Workspace"
    assert result.root_path == str(tmp_path.resolve())

    repository.create.assert_called_once()
