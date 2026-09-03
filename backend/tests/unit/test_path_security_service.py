from pathlib import Path

import pytest

from backend.app.services.path_security_service import (
    PathSecurityError,
    PathSecurityService,
)


def test_valid_directory(
    tmp_path: Path,
) -> None:
    service = PathSecurityService()

    result = service.validate(
        str(tmp_path),
    )

    assert result == tmp_path.resolve()


def test_rejects_relative_path() -> None:
    service = PathSecurityService()

    with pytest.raises(PathSecurityError):
        service.validate(
            "relative/path",
        )


def test_rejects_missing_path(
    tmp_path: Path,
) -> None:
    service = PathSecurityService()

    missing = tmp_path / "does-not-exist"

    with pytest.raises(PathSecurityError):
        service.validate(
            str(missing),
        )


def test_rejects_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "test.txt"

    file_path.write_text(
        "NEXUS",
        encoding="utf-8",
    )

    service = PathSecurityService()

    with pytest.raises(PathSecurityError):
        service.validate(
            str(file_path),
        )


def test_is_within(
    tmp_path: Path,
) -> None:
    service = PathSecurityService()

    root = tmp_path / "root"
    child = root / "child"

    root.mkdir()
    child.mkdir()

    assert service.is_within(
        child,
        root,
    )


def test_is_not_within(
    tmp_path: Path,
) -> None:
    service = PathSecurityService()

    root = tmp_path / "root"
    outside = tmp_path / "outside"

    root.mkdir()
    outside.mkdir()

    assert not service.is_within(
        outside,
        root,
    )


def test_validate_file_rejects_path_traversal(
    tmp_path: Path,
) -> None:
    service = PathSecurityService()

    workspace = tmp_path / "workspace"
    secret = tmp_path / "secret.txt"

    workspace.mkdir()

    secret.write_text(
        "SECRET",
        encoding="utf-8",
    )

    malicious = workspace / ".." / "secret.txt"

    with pytest.raises(PathSecurityError):
        service.validate_file(
            malicious,
            workspace,
        )
