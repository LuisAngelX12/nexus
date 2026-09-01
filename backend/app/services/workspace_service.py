from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.workspace import Workspace
from backend.app.repositories.workspace_repository import (
    WorkspaceRepository,
)
from backend.app.schemas.workspace import WorkspaceCreate


class WorkspaceService:
    def __init__(self, session: Session) -> None:
        self.repository = WorkspaceRepository(session)

    def create_workspace(
        self,
        user_id: UUID,
        data: WorkspaceCreate,
    ) -> Workspace:
        root = Path(data.root_path).expanduser().resolve()

        if not root.exists():
            raise FileNotFoundError(root)

        if not root.is_dir():
            raise ValueError("Workspace path must be a directory.")

        workspace = Workspace(
            user_id=user_id,
            name=data.name.strip(),
            root_path=str(root),
        )

        return self.repository.create(workspace)
