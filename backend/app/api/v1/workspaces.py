from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.repositories.workspace_repository import (
    WorkspaceRepository,
)
from backend.app.schemas.scan import ScanResult
from backend.app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
)
from backend.app.services.workspace_scan_service import (
    WorkspaceScanService,
)
from backend.app.services.workspace_service import (
    WorkspaceService,
)


router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
)

@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    service = WorkspaceService(db)

    try:
        workspace = service.create_workspace(
            user_id=current_user.id,
            data=data,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory does not exist.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return WorkspaceResponse.model_validate(workspace)

@router.post(
    "/{workspace_id}/scan",
    response_model=ScanResult,
)
def scan_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanResult:
    repository = WorkspaceRepository(db)

    workspace = repository.get_by_id(workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    if workspace.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    service = WorkspaceScanService(db)

    result = service.scan(workspace)

    return ScanResult(
        workspace_id=workspace.id,
        **result,
    )