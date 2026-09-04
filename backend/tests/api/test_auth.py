from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from backend.app.api.dependencies import get_db
from backend.app.main import app


@pytest.fixture
def client(session: Session) -> Generator[TestClient, Any]:
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()


def register_user(
    client: TestClient,
    email: str,
    password: str = "Password123!",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 201

    return response.json()


def login_user(
    client: TestClient,
    email: str,
    password: str = "Password123!",
) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()


def test_login_success(client: TestClient) -> None:
    email = "login@example.com"

    register_user(
        client,
        email,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "Password123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient) -> None:
    email = "invalid-login@example.com"

    register_user(
        client,
        email,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_auth_me_requires_authentication(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me",
    )

    assert response.status_code == 401


def test_auth_me_returns_current_user(client: TestClient) -> None:
    email = "me@example.com"

    register_user(
        client,
        email,
    )

    token_data = login_user(
        client,
        email,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token_data['access_token']}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"


def test_create_workspace(
    client: TestClient,
    tmp_path: Path,
) -> None:
    email = "workspace@example.com"

    register_user(
        client,
        email,
    )

    token_data = login_user(
        client,
        email,
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    response = client.post(
        "/api/v1/workspaces",
        headers={
            "Authorization": f"Bearer {token_data['access_token']}",
        },
        json={
            "name": "Test Workspace",
            "root_path": str(workspace_path),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Workspace"
    assert data["root_path"] == str(workspace_path.resolve())
    assert "id" in data


def test_create_workspace_requires_authentication(
    client: TestClient,
    tmp_path: Path,
) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "Test Workspace",
            "root_path": str(workspace_path),
        },
    )

    assert response.status_code == 401


def test_create_workspace_rejects_relative_path(
    client: TestClient,
) -> None:
    email = "invalid-workspace@example.com"

    register_user(
        client,
        email,
    )

    token_data = login_user(
        client,
        email,
    )

    response = client.post(
        "/api/v1/workspaces",
        headers={
            "Authorization": f"Bearer {token_data['access_token']}",
        },
        json={
            "name": "Invalid Workspace",
            "root_path": "relative/workspace",
        },
    )

    assert response.status_code == 400


def test_workspace_ownership(
    client: TestClient,
    tmp_path: Path,
) -> None:
    user_a_email = "user-a@example.com"
    user_b_email = "user-b@example.com"

    register_user(
        client,
        user_a_email,
    )

    register_user(
        client,
        user_b_email,
    )

    token_a = login_user(
        client,
        user_a_email,
    )

    token_b = login_user(
        client,
        user_b_email,
    )

    workspace_path = tmp_path / "workspace-b"
    workspace_path.mkdir()

    create_response = client.post(
        "/api/v1/workspaces",
        headers={
            "Authorization": f"Bearer {token_b['access_token']}",
        },
        json={
            "name": "Workspace B",
            "root_path": str(workspace_path),
        },
    )

    assert create_response.status_code == 201

    workspace = create_response.json()
    workspace_id = workspace["id"]

    with patch(
        "backend.app.api.v1.workspaces.scan_workspace_task",
    ) as mock_task:
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/scan",
            headers={
                "Authorization": f"Bearer {token_a['access_token']}",
            },
        )

    assert response.status_code == 404
    mock_task.delay.assert_not_called()

    assert response.status_code == 404


def test_workspace_owner_can_start_scan(
    client: TestClient,
    tmp_path: Path,
) -> None:
    email = "workspace-owner@example.com"

    register_user(
        client,
        email,
    )

    token_data = login_user(
        client,
        email,
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    create_response = client.post(
        "/api/v1/workspaces",
        headers={
            "Authorization": f"Bearer {token_data['access_token']}",
        },
        json={
            "name": "Owner Workspace",
            "root_path": str(workspace_path),
        },
    )

    assert create_response.status_code == 201

    workspace_id = create_response.json()["id"]

    with patch(
        "backend.app.api.v1.workspaces.scan_workspace_task",
    ) as mock_task:
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/scan",
            headers={
                "Authorization": f"Bearer {token_data['access_token']}",
            },
        )

    assert response.status_code == 202
    mock_task.delay.assert_called_once()

    assert response.status_code == 202
