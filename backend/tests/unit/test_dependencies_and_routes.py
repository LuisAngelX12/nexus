from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.dependencies import get_current_user
from backend.app.api.routes.ready import readiness_check
from backend.app.api.v1.auth import login, register
from backend.app.api.v1.files import index_file
from backend.app.api.v1.workspaces import create_workspace, scan_workspace
from backend.app.models import Job, JobStatus, JobType
from backend.app.models.file import File
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserLogin
from backend.app.services.file_service import DuplicateFileError
from backend.app.services.path_security_service import PathSecurityError
from backend.app.services.user_service import UserAlreadyExistsError


def make_user(
    user_id: UUID | None = None,
    is_active: bool = True,
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id or uuid4()
    user.is_active = is_active

    return user


def make_workspace(
    workspace_id: UUID | None = None,
    user_id: UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=workspace_id or uuid4(),
        user_id=user_id or uuid4(),
    )


def make_workspace_repository(
    workspace: SimpleNamespace,
) -> MagicMock:
    repository = MagicMock()
    repository.get_by_id.return_value = workspace

    return repository


def make_credentials(
    token: str = "valid-token",
) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )


def assert_unauthorized(
    exc_info: pytest.ExceptionInfo[HTTPException],
) -> None:
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication credentials"
    assert exc_info.value.headers is not None
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


def test_get_current_user_rejects_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    credentials = make_credentials("invalid-token")

    def raise_invalid_token(_token: str) -> None:
        raise ValueError("invalid token")

    monkeypatch.setattr(
        "backend.app.api.dependencies.decode_access_token",
        raise_invalid_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials, db)

    assert_unauthorized(exc_info)


def test_get_current_user_rejects_missing_sub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    credentials = make_credentials()

    def return_empty_payload(_token: str) -> dict[str, str]:
        return {}

    monkeypatch.setattr(
        "backend.app.api.dependencies.decode_access_token",
        return_empty_payload,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials, db)

    assert_unauthorized(exc_info)


def test_get_current_user_rejects_inactive_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    credentials = make_credentials()

    user = make_user(is_active=False)

    monkeypatch.setattr(
        "backend.app.api.dependencies.decode_access_token",
        lambda _token: {"sub": str(user.id)},
    )

    repository = MagicMock()
    repository.get_by_id.return_value = user

    monkeypatch.setattr(
        "backend.app.api.dependencies.UserRepository",
        lambda _session: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials, db)

    assert_unauthorized(exc_info)


def test_get_current_user_returns_active_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    credentials = make_credentials()

    user = make_user()

    monkeypatch.setattr(
        "backend.app.api.dependencies.decode_access_token",
        lambda _token: {"sub": str(user.id)},
    )

    repository = MagicMock()
    repository.get_by_id.return_value = user

    monkeypatch.setattr(
        "backend.app.api.dependencies.UserRepository",
        lambda _session: repository,
    )

    result = get_current_user(credentials, db)

    assert result is user
    repository.get_by_id.assert_called_once_with(user.id)


@pytest.mark.anyio
async def test_readiness_check() -> None:
    result = await readiness_check()

    assert result == {"status": "ready"}


def test_register_duplicate_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = UserCreate(
        email="test@example.com",
        password="password",
        first_name="Test",
        last_name="User",
    )

    service = MagicMock()
    service.create_user.side_effect = UserAlreadyExistsError(
        "A user with this email already exists.",
    )

    monkeypatch.setattr(
        "backend.app.api.v1.auth.UserService",
        lambda _db: service,
    )

    with pytest.raises(HTTPException) as exc_info:
        register(data, MagicMock())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == ("A user with this email already exists.")


def test_login_invalid_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = UserLogin(
        email="test@example.com",
        password="wrong-password",
    )

    service = MagicMock()
    service.authenticate_user.return_value = None

    monkeypatch.setattr(
        "backend.app.api.v1.auth.UserService",
        lambda _db: service,
    )

    with pytest.raises(HTTPException) as exc_info:
        login(data, MagicMock())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"
    assert exc_info.value.headers is not None
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


def test_index_file_workspace_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MagicMock()
    repository.get_by_id.return_value = None

    monkeypatch.setattr(
        "backend.app.api.v1.files.WorkspaceRepository",
        lambda _db: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        index_file(
            path="test.txt",
            workspace_id=uuid4(),
            db=MagicMock(),
            current_user=make_user(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Workspace not found."


def test_index_file_workspace_belongs_to_other_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_user = make_user()
    workspace = make_workspace(user_id=uuid4())
    repository = make_workspace_repository(workspace)

    monkeypatch.setattr(
        "backend.app.api.v1.files.WorkspaceRepository",
        lambda _db: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        index_file(
            path="test.txt",
            workspace_id=workspace.id,
            db=MagicMock(),
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Workspace not found."


def test_index_file_file_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    workspace = make_workspace(user_id=user.id)
    repository = make_workspace_repository(workspace)

    service = MagicMock()
    service.index_file.side_effect = FileNotFoundError()

    monkeypatch.setattr(
        "backend.app.api.v1.files.WorkspaceRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.files.FileService",
        lambda _db: service,
    )

    with pytest.raises(HTTPException) as exc_info:
        index_file(
            path="missing.txt",
            workspace_id=workspace.id,
            db=MagicMock(),
            current_user=user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "File not found."


def test_index_file_invalid_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    workspace = make_workspace(user_id=user.id)
    repository = make_workspace_repository(workspace)

    service = MagicMock()
    service.index_file.side_effect = ValueError("Invalid file.")

    monkeypatch.setattr(
        "backend.app.api.v1.files.WorkspaceRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.files.FileService",
        lambda _db: service,
    )

    with pytest.raises(HTTPException) as exc_info:
        index_file(
            path="bad.txt",
            workspace_id=workspace.id,
            db=MagicMock(),
            current_user=user,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid file."


def test_index_file_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    workspace = make_workspace(user_id=user.id)
    repository = make_workspace_repository(workspace)

    existing_file = MagicMock(spec=File)
    existing_file.id = uuid4()
    existing_file.name = "existing.txt"

    service = MagicMock()
    service.index_file.side_effect = DuplicateFileError(existing_file)

    monkeypatch.setattr(
        "backend.app.api.v1.files.WorkspaceRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.files.FileService",
        lambda _db: service,
    )

    with pytest.raises(HTTPException) as exc_info:
        index_file(
            path="duplicate.txt",
            workspace_id=workspace.id,
            db=MagicMock(),
            current_user=user,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {
        "message": "Duplicate file detected.",
        "existing_file_id": str(existing_file.id),
        "existing_file_name": existing_file.name,
    }


def test_create_workspace_invalid_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    security_service = MagicMock()
    security_service.validate.side_effect = PathSecurityError(
        "Invalid workspace path.",
    )

    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.PathSecurityService",
        lambda: security_service,
    )

    data = MagicMock(root_path="C:/invalid")

    with pytest.raises(HTTPException) as exc_info:
        create_workspace(
            data=data,
            db=MagicMock(),
            current_user=make_user(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid workspace path."


def test_create_workspace_missing_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path.cwd()

    security_service = MagicMock()
    security_service.validate.return_value = root

    service = MagicMock()
    service.create_workspace.side_effect = FileNotFoundError(root)

    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.PathSecurityService",
        lambda: security_service,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.WorkspaceService",
        lambda _db: service,
    )

    data = MagicMock(root_path=str(root))

    with pytest.raises(HTTPException) as exc_info:
        create_workspace(
            data=data,
            db=MagicMock(),
            current_user=make_user(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Workspace directory does not exist."


def test_create_workspace_invalid_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path.cwd()

    security_service = MagicMock()
    security_service.validate.return_value = root

    service = MagicMock()
    service.create_workspace.side_effect = ValueError(
        "Invalid workspace.",
    )

    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.PathSecurityService",
        lambda: security_service,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.WorkspaceService",
        lambda _db: service,
    )

    data = MagicMock(root_path=str(root))

    with pytest.raises(HTTPException) as exc_info:
        create_workspace(
            data=data,
            db=MagicMock(),
            current_user=make_user(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid workspace."


def test_scan_workspace_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MagicMock()
    repository.get_by_id_for_user.return_value = None

    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.WorkspaceRepository",
        lambda _db: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        scan_workspace(
            workspace_id=uuid4(),
            db=MagicMock(),
            current_user=make_user(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Workspace not found."


def test_scan_workspace_dispatches_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    workspace = make_workspace(user_id=user.id)
    job_id = uuid4()
    created_at = datetime.now(UTC)

    repository = MagicMock()
    repository.get_by_id_for_user.return_value = workspace

    job = Job(
        id=job_id,
        workspace_id=workspace.id,
        type=JobType.WORKSPACE_SCAN,
        status=JobStatus.QUEUED,
        progress=0,
        total_files=0,
        files_found=0,
        files_processed=0,
        duplicates=0,
        skipped_files=0,
        permission_errors=0,
        created_at=created_at,
        started_at=None,
        finished_at=None,
        error_message=None,
    )

    job_repository = MagicMock()
    job_repository.create.return_value = job

    task = MagicMock()

    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.WorkspaceRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.JobRepository",
        lambda _db: job_repository,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.scan_workspace_task",
        task,
    )

    result = scan_workspace(
        workspace_id=workspace.id,
        db=MagicMock(),
        current_user=user,
    )

    assert result.id == job_id
    assert result.status == JobStatus.QUEUED
    assert result.progress == 0
    assert result.created_at == created_at

    task.delay.assert_called_once_with(
        str(job_id),
        str(workspace.id),
    )


def test_index_file_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    workspace_id = uuid4()
    file_id = uuid4()

    workspace = SimpleNamespace(
        id=workspace_id,
        user_id=user.id,
    )

    indexed_file = SimpleNamespace(
        id=file_id,
        workspace_id=workspace_id,
        name="test.txt",
        path="C:/workspace/test.txt",
        size=5,
        mime_type="text/plain",
        extension=".txt",
        sha256="abc123",
    )

    workspace_repository = MagicMock()
    workspace_repository.get_by_id.return_value = workspace

    service = MagicMock()
    service.index_file.return_value = indexed_file

    monkeypatch.setattr(
        "backend.app.api.v1.files.WorkspaceRepository",
        lambda _db: workspace_repository,
    )
    monkeypatch.setattr(
        "backend.app.api.v1.files.FileService",
        lambda _db: service,
    )

    result = index_file(
        path="C:/workspace/test.txt",
        workspace_id=workspace_id,
        db=MagicMock(),
        current_user=user,
    )

    assert result.id == file_id
    assert result.name == "test.txt"

    service.index_file.assert_called_once_with(
        workspace_id=workspace_id,
        file_path=Path("C:/workspace/test.txt"),
    )


def test_scan_workspace_belongs_to_other_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    owner = make_user()
    current_user = make_user()

    workspace = make_workspace(
        user_id=owner.id,
    )

    repository = MagicMock()
    repository.get_by_id_for_user.return_value = workspace

    monkeypatch.setattr(
        "backend.app.api.v1.workspaces.WorkspaceRepository",
        lambda _db: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        scan_workspace(
            workspace_id=workspace_id,
            db=MagicMock(),
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Workspace not found."

    repository.get_by_id_for_user.assert_called_once_with(
        workspace_id,
        current_user.id,
    )
