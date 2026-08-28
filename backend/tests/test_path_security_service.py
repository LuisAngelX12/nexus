from pathlib import Path

import pytest

from backend.app.services.path_security_service import (
    PathOutsideWorkspaceError,
    validate_path_inside_workspace,
)


def test_path_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "documents"
    workspace.mkdir()

    file = workspace / "test.txt"
    file.write_text("NEXUS", encoding="utf-8")

    result = validate_path_inside_workspace(
        workspace,
        file,
    )

    assert result == file.resolve()


def test_path_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "documents"
    workspace.mkdir()

    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    with pytest.raises(PathOutsideWorkspaceError):
        validate_path_inside_workspace(
            workspace,
            outside_file,
        )