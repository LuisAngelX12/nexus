from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.file import FileResponse
from backend.app.services.file_service import (
    DuplicateFileError,
    FileService,
)


router = APIRouter(
    prefix="/files",
    tags=["Files"],
)


@router.post(
    "/index",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
)
def index_file(
    path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    service = FileService(db)

    try:
        file = service.index_file(
            user_id=current_user.id,
            file_path=Path(path),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except DuplicateFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Duplicate file detected.",
                "existing_file_id": str(exc.existing_file.id),
                "existing_file_name": exc.existing_file.name,
            },
        )

    return FileResponse.model_validate(file)