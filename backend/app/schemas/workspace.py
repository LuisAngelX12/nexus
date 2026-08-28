from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    root_path: str = Field(
        min_length=1,
        max_length=2000,
    )


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    root_path: str