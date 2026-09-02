from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: UUID
    status: str
    progress: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    model_config = {
        "from_attributes": True,
    }