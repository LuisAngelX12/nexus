from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.security import verify_password
from backend.app.models.job import Job, JobStatus, JobType
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.user import UserCreate
from backend.app.services.user_service import UserService

PASSWORD = "Password123!"


def create_user(
    session: Session,
    email: str,
) -> User:
    service = UserService(session)

    return service.create_user(
        UserCreate(
            email=email,
            password=PASSWORD,
            first_name="Test",
            last_name="User",
        ),
    )


def create_workspace(
    session: Session,
    user: User,
    root_path: Path,
) -> Workspace:
    workspace = Workspace(
        user_id=user.id,
        name="Test Workspace",
        root_path=str(root_path),
    )

    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    return workspace


def create_job(
    session: Session,
    workspace: Workspace,
    job_status: JobStatus = JobStatus.QUEUED,
) -> Job:
    job = Job(
        workspace_id=workspace.id,
        type=JobType.WORKSPACE_SCAN,
        status=job_status,
        progress=0,
        total_files=0,
        files_found=0,
        files_processed=0,
        duplicates=0,
        skipped_files=0,
        permission_errors=0,
    )

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


def login(
    client: TestClient,
    email: str,
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


def test_get_existing_job(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    user = create_user(
        session,
        "job@example.com",
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    workspace = create_workspace(
        session,
        user,
        workspace_path,
    )

    job = create_job(
        session,
        workspace,
    )

    token = login(
        client,
        "job@example.com",
    )

    response = client.get(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(job.id)
    assert data["status"] == "queued"
    assert data["progress"] == 0


def test_get_nonexistent_job(
    client: TestClient,
    session: Session,
) -> None:
    create_user(
        session,
        "missing-job@example.com",
    )

    token = login(
        client,
        "missing-job@example.com",
    )

    response = client.get(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_get_job_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
    )

    assert response.status_code == 401


def test_user_cannot_access_another_users_job(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    create_user(
        session,
        "user-a@example.com",
    )

    user_b = create_user(
        session,
        "user-b@example.com",
    )

    workspace_path = tmp_path / "workspace-b"
    workspace_path.mkdir()

    workspace_b = create_workspace(
        session,
        user_b,
        workspace_path,
    )

    job_b = create_job(
        session,
        workspace_b,
    )

    token_a = login(
        client,
        "user-a@example.com",
    )

    response = client.get(
        f"/api/v1/jobs/{job_b.id}",
        headers=auth_headers(token_a),
    )

    assert response.status_code == 404


def test_cancel_queued_job(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    user = create_user(
        session,
        "cancel-queued@example.com",
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    workspace = create_workspace(
        session,
        user,
        workspace_path,
    )

    job = create_job(
        session,
        workspace,
        JobStatus.QUEUED,
    )

    token = login(
        client,
        "cancel-queued@example.com",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/cancel",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(job.id)
    assert data["status"] == "cancelled"


def test_cancel_running_job(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    user = create_user(
        session,
        "cancel-running@example.com",
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    workspace = create_workspace(
        session,
        user,
        workspace_path,
    )

    job = create_job(
        session,
        workspace,
        JobStatus.RUNNING,
    )

    token = login(
        client,
        "cancel-running@example.com",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/cancel",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(job.id)
    assert data["status"] == "cancelling"


def test_completed_job_cannot_be_cancelled(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    user = create_user(
        session,
        "cancel-completed@example.com",
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    workspace = create_workspace(
        session,
        user,
        workspace_path,
    )

    job = create_job(
        session,
        workspace,
        JobStatus.COMPLETED,
    )

    token = login(
        client,
        "cancel-completed@example.com",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/cancel",
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_failed_job_cannot_be_cancelled(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    user = create_user(
        session,
        "cancel-failed@example.com",
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    workspace = create_workspace(
        session,
        user,
        workspace_path,
    )

    job = create_job(
        session,
        workspace,
        JobStatus.FAILED,
    )

    token = login(
        client,
        "cancel-failed@example.com",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/cancel",
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_cancelled_job_cannot_be_cancelled_again(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    user = create_user(
        session,
        "cancel-cancelled@example.com",
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    workspace = create_workspace(
        session,
        user,
        workspace_path,
    )

    job = create_job(
        session,
        workspace,
        JobStatus.CANCELLED,
    )

    token = login(
        client,
        "cancel-cancelled@example.com",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/cancel",
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_user_cannot_cancel_another_users_job(
    client: TestClient,
    session: Session,
    tmp_path: Path,
) -> None:
    create_user(
        session,
        "cancel-user-a@example.com",
    )

    user_b = create_user(
        session,
        "cancel-user-b@example.com",
    )

    workspace_path = tmp_path / "workspace-b"
    workspace_path.mkdir()

    workspace_b = create_workspace(
        session,
        user_b,
        workspace_path,
    )

    job_b = create_job(
        session,
        workspace_b,
        JobStatus.QUEUED,
    )

    token_a = login(
        client,
        "cancel-user-a@example.com",
    )

    response = client.post(
        f"/api/v1/jobs/{job_b.id}/cancel",
        headers=auth_headers(token_a),
    )

    assert response.status_code == 404

    session.refresh(job_b)

    assert job_b.status == JobStatus.QUEUED


def test_created_user_can_verify_password(
    session: Session,
) -> None:
    user = create_user(
        session,
        "password-test@example.com",
    )

    assert verify_password(
        PASSWORD,
        user.password_hash,
    )
