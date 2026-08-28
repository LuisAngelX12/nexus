from pathlib import Path

from backend.app.services.file_hash_service import calculate_sha256


def test_calculate_sha256(tmp_path: Path) -> None:
    file = tmp_path / "test.txt"

    file.write_text(
        "NEXUS",
        encoding="utf-8",
    )

    result = calculate_sha256(file)

    assert result == (
        "52b797a276d825aaa28f449f1d35682bd4d271f6455be84e3869cdd7aed2ca03"
    )