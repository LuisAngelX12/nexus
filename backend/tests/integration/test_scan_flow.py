import time
import uuid
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"


def _json_object(response: httpx.Response) -> dict[str, Any]:
    data = response.json()

    assert isinstance(data, dict)

    return data


def test_scan_flow_authentication() -> None:
    unique_email = f"integration-{uuid.uuid4().hex[:12]}@gmail.com"
    password = "IntegrationPassword123!"

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # ---------------------------------------------------------
        # 1. Registrar usuario
        # ---------------------------------------------------------
        register_response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": password,
                "first_name": "Integration",
                "last_name": "Test",
            },
        )

        assert register_response.status_code == 201

        user = _json_object(register_response)

        assert user["email"] == unique_email
        assert user["is_active"] is True

        # ---------------------------------------------------------
        # 2. Login
        # ---------------------------------------------------------
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": password,
            },
        )

        assert login_response.status_code == 200

        login_data = _json_object(login_response)

        assert login_data["access_token"]
        assert login_data["token_type"] == "bearer"

        token = login_data["access_token"]

        headers = {
            "Authorization": f"Bearer {token}",
        }

        # ---------------------------------------------------------
        # 3. Comprobar identidad autenticada
        # ---------------------------------------------------------
        me_response = client.get(
            "/auth/me",
            headers=headers,
        )

        assert me_response.status_code == 200

        me = _json_object(me_response)

        assert me["email"] == unique_email
        assert me["id"] == user["id"]

        # ---------------------------------------------------------
        # 4. Crear workspace
        # ---------------------------------------------------------
        workspace_response = client.post(
            "/workspaces",
            json={
                "name": "Integration Workspace",
                "root_path": "/data/test-workspace",
            },
            headers=headers,
        )

        assert workspace_response.status_code == 201

        workspace = _json_object(workspace_response)

        assert workspace["id"]
        assert workspace["name"] == "Integration Workspace"
        assert workspace["root_path"] == "/data/test-workspace"

        workspace_id = workspace["id"]

        # ---------------------------------------------------------
        # 5. Iniciar scan
        # ---------------------------------------------------------
        scan_response = client.post(
            f"/workspaces/{workspace_id}/scan",
            headers=headers,
        )

        assert scan_response.status_code == 202

        job = _json_object(scan_response)

        assert job["id"]
        assert job["status"] == "queued"
        assert job["progress"] == 0
        assert job["finished_at"] is None

        job_id = job["id"]

        # ---------------------------------------------------------
        # 6. Esperar a que Celery complete el Job
        # ---------------------------------------------------------
        timeout = 30.0
        start = time.monotonic()

        final_job: dict[str, Any] | None = None

        while time.monotonic() - start < timeout:
            job_response = client.get(
                f"/jobs/{job_id}",
                headers=headers,
            )

            assert job_response.status_code == 200

            current_job = _json_object(job_response)

            if current_job["status"] in {
                "completed",
                "failed",
                "cancelled",
            }:
                final_job = current_job
                break

            time.sleep(0.5)

        assert final_job is not None

        assert final_job["status"] == "completed"
        assert final_job["progress"] == 100
        assert final_job["finished_at"] is not None
        assert final_job["error_message"] is None
