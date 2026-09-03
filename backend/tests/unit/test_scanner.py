from pathlib import Path

from backend.app.services.file_scanner import scan_directory


def test_scanner_finds_files(tmp_path: Path) -> None:
    (tmp_path / "file1.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    (tmp_path / "file2.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    files = list(scan_directory(tmp_path))

    assert len(files) == 2


def test_empty_directory(tmp_path: Path) -> None:
    files = list(scan_directory(tmp_path))

    assert len(files) == 0


def test_scanner_finds_files_recursively(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    src = tmp_path / "src"
    src.mkdir()

    (src / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    (src / "utils.py").write_text(
        "print('utils')",
        encoding="utf-8",
    )

    docs = tmp_path / "docs"
    docs.mkdir()

    (docs / "README.md").write_text(
        "# NEXUS",
        encoding="utf-8",
    )

    files = list(scan_directory(tmp_path))

    assert len(files) == 4
