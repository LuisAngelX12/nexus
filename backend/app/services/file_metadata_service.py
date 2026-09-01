from datetime import datetime, timezone
from pathlib import Path


def get_file_modified_at(path: Path) -> datetime:
    timestamp = path.stat().st_mtime

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )