from uuid import UUID

from pydantic import BaseModel


class ScanResult(BaseModel):
    workspace_id: UUID
    files_found: int
    new_files: int
    unchanged_files: int
    modified_files: int
    duplicates: int
    missing_files: int
    errors: int