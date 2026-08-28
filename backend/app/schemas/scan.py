from uuid import UUID

from pydantic import BaseModel


class ScanResult(BaseModel):
    workspace_id: UUID
    files_found: int
    files_indexed: int
    duplicates: int
    errors: int