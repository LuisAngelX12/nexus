from collections.abc import Iterator
from pathlib import Path


def scan_directory(
    root: Path,
) -> Iterator[Path]:
    root = root.resolve()

    if not root.exists():
        raise FileNotFoundError(root)

    if not root.is_dir():
        raise ValueError(
            "The workspace root is not a directory."
        )

    for path in root.rglob("*"):
        if path.is_file():
            yield path