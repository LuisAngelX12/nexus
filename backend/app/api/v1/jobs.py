from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.models import Job, JobStatus, Workspace
from backend.app.models.user import User
from backend.app.repositories.job_repository import JobRepository
from backend.app.repositories.workspace_repository import WorkspaceRepository
from backend.app.schemas.job import JobResponse

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    repository = JobRepository(db)

    job = repository.get_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    workspace_repository = WorkspaceRepository(db)

    workspace = workspace_repository.get_by_id(
        job.workspace_id,
    )

    if workspace is None or workspace.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return JobResponse.model_validate(job)


@router.post(
    "/{job_id}/cancel",
    response_model=JobResponse,
)
def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    job = (
        db.query(Job)
        .join(Workspace, Workspace.id == Job.workspace_id)
        .filter(
            Job.id == job_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    if job.status == JobStatus.QUEUED:
        job.status = JobStatus.CANCELLED

    elif job.status == JobStatus.RUNNING:
        job.status = JobStatus.CANCELLING

    else:
        raise HTTPException(
            status_code=409,
            detail="Job cannot be cancelled.",
        )

    db.commit()
    db.refresh(job)

    return JobResponse.model_validate(job)
