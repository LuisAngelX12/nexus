from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.workspace import Workspace


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(
        self,
        workspace_id: UUID,
    ) -> Workspace | None:
        statement = select(Workspace).where(
            Workspace.id == workspace_id
        )

        return self.session.scalar(statement)

    def get_by_user(
        self,
        user_id: UUID,
    ) -> list[Workspace]:
        statement = select(Workspace).where(
            Workspace.user_id == user_id
        )

        return list(self.session.scalars(statement))

    def get_by_id_for_user(
            self,
            workspace_id: UUID,
            user_id: UUID,
    ) -> Workspace | None:
        statement = select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
        )

        return self.session.scalar(statement)

    def create(
        self,
        workspace: Workspace,
    ) -> Workspace:
        self.session.add(workspace)
        self.session.commit()
        self.session.refresh(workspace)

        return workspace