from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.app.models.job import JobStatus, JobType


class JobResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    workspace_id: UUID
    type: JobType
    status: JobStatus
    progress: int
    files_found: int
    files_processed: int
    duplicates: int
    error_message: str | None