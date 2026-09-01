from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.workspace_scan_service import (
    WorkspaceScanService,
)


def test_scan_detects_duplicates(
    session: Session,
    tmp_path: Path,
) -> None:
    user = User(
        email="scanner@example.com",
        password_hash="test-hash",
        first_name="Scanner",
        last_name="Test",
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    first = workspace_path / "first.txt"
    second = workspace_path / "second.txt"
    third = workspace_path / "third.txt"

    first.write_text(
        "same content",
        encoding="utf-8",
    )

    second.write_text(
        "same content",
        encoding="utf-8",
    )

    third.write_text(
        "different content",
        encoding="utf-8",
    )

    workspace = Workspace(
        user_id=user.id,
        name="Test Workspace",
        root_path=str(workspace_path),
    )

    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    service = WorkspaceScanService(session)

    result = service.scan(workspace)

    assert result["files_found"] == 3
    assert result["files_indexed"] == 2
    assert result["duplicates"] == 1
    assert result["errors"] == 0
