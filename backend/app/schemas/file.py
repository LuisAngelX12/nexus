from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    path: str
    size: int
    mime_type: str | None
    extension: str | None
    sha256: str