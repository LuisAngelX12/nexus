from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.jobs.celery_app import celery_app
from backend.app.jobs.exceptions import JobCancelled
from backend.app.models.job import Job, JobStatus
from backend.app.models.workspace import Workspace
from backend.app.services.workspace_scan_service import (
    WorkspaceScanService,
)


def update_job_progress(
    session: Session,
    job_id: UUID,
    processed: int,
    total: int,
) -> None:
    job = session.get(
        Job,
        job_id,
    )

    if job is None:
        return

    job.files_processed = processed
    job.total_files = total

    job.progress = (
        int(processed * 100 / total)
        if total > 0
        else 100
    )

    session.commit()


def is_job_cancelling(
    session: Session,
    job_id: UUID,
) -> bool:
    job = session.get(
        Job,
        job_id,
    )

    if job is None:
        return True

    return job.status == JobStatus.CANCELLING


@celery_app.task(
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={
        "max_retries": 3,
    },
    name="nexus.scan_workspace",
)
def scan_workspace_task(
    job_id: str,
    workspace_id: str,
) -> None:
    job_session = SessionLocal()
    scanner_session = SessionLocal()

    job_uuid = UUID(job_id)
    workspace_uuid = UUID(workspace_id)

    try:
        job = job_session.get(
            Job,
            job_uuid,
        )

        if job is None:
            return

        workspace = scanner_session.get(
            Workspace,
            workspace_uuid,
        )

        if workspace is None:
            job.status = JobStatus.FAILED
            job.error_message = "Workspace not found."
            job.finished_at = datetime.now(timezone.utc)
            job_session.commit()
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job_session.commit()

        def progress_callback(
            processed: int,
            total: int,
        ) -> None:
            if is_job_cancelling(
                job_session,
                job_uuid,
            ):
                raise JobCancelled

            update_job_progress(
                job_session,
                job_uuid,
                processed,
                total,
            )

        service = WorkspaceScanService(
            scanner_session,
        )

        result = service.scan(
            workspace,
            progress_callback=progress_callback,
        )

        scanner_session.commit()

        job = job_session.get(
            Job,
            job_uuid,
        )

        if job is not None:
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.finished_at = datetime.now(timezone.utc)
            job.files_found = result["files_found"]
            job.files_processed = (
                result["new_files"]
                + result["unchanged_files"]
                + result["modified_files"]
            )
            job.total_files = result["files_found"]
            job.duplicates = result["duplicates"]

            job_session.commit()

    except JobCancelled:
        scanner_session.rollback()
        job_session.rollback()

        job = job_session.get(
            Job,
            job_uuid,
        )

        if job is not None:
            job.status = JobStatus.CANCELLED
            job.finished_at = datetime.now(timezone.utc)
            job_session.commit()

        return

    except Exception as exc:
        scanner_session.rollback()
        job_session.rollback()

        job = job_session.get(
            Job,
            job_uuid,
        )

        if job is not None:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            job_session.commit()

        raise

    finally:
        scanner_session.close()
        job_session.close()
