from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.app.jobs.tasks import (
    is_job_cancelling,
    scan_workspace_task,
    update_job_progress,
)
from backend.app.models.job import JobStatus


def mock_session_local(monkeypatch, job_session, scanner_session):
    sessions = iter([
        job_session,
        scanner_session,
    ])

    monkeypatch.setattr(
        "backend.app.jobs.tasks.SessionLocal",
        lambda: next(sessions),
    )


def test_update_job_progress_job_not_found():
    session = MagicMock()
    session.get.return_value = None

    job_id = uuid4()

    update_job_progress(
        session=session,
        job_id=job_id,
        processed=5,
        total=10,
    )

    session.get.assert_called_once_with(
        # Importing Job here would be another option,
        # but we only care about the behavior.
        pytest.importorskip("backend.app.models.job").Job,
        job_id,
    )

    session.commit.assert_not_called()


def test_update_job_progress():
    session = MagicMock()

    job = MagicMock()
    session.get.return_value = job

    job_id = uuid4()

    update_job_progress(
        session=session,
        job_id=job_id,
        processed=5,
        total=10,
    )

    assert job.files_processed == 5
    assert job.total_files == 10
    assert job.progress == 50

    session.commit.assert_called_once()


def test_update_job_progress_zero_total():
    session = MagicMock()

    job = MagicMock()
    session.get.return_value = job

    update_job_progress(
        session=session,
        job_id=uuid4(),
        processed=0,
        total=0,
    )

    assert job.files_processed == 0
    assert job.total_files == 0
    assert job.progress == 100

    session.commit.assert_called_once()


def test_is_job_cancelling_job_not_found():
    session = MagicMock()
    session.get.return_value = None

    result = is_job_cancelling(
        session=session,
        job_id=uuid4(),
    )

    assert result is True


def test_is_job_cancelling_false():
    session = MagicMock()

    job = MagicMock()
    job.status = JobStatus.RUNNING

    session.get.return_value = job

    result = is_job_cancelling(
        session=session,
        job_id=uuid4(),
    )

    assert result is False


def test_is_job_cancelling_true():
    session = MagicMock()

    job = MagicMock()
    job.status = JobStatus.CANCELLING

    session.get.return_value = job

    result = is_job_cancelling(
        session=session,
        job_id=uuid4(),
    )

    assert result is True


def test_scan_workspace_task_job_not_found(monkeypatch):
    job_session = MagicMock()
    scanner_session = MagicMock()

    job_session.get.return_value = None

    mock_session_local(
        monkeypatch,
        job_session,
        scanner_session,
    )

    scan_workspace_task.run(
        str(uuid4()),
        str(uuid4()),
    )

    scanner_session.close.assert_called_once()
    job_session.close.assert_called_once()


def test_scan_workspace_task_workspace_not_found(monkeypatch):
    job_session = MagicMock()
    scanner_session = MagicMock()

    job = MagicMock()

    job_session.get.return_value = job
    scanner_session.get.return_value = None

    mock_session_local(
        monkeypatch,
        job_session,
        scanner_session,
    )

    scan_workspace_task.run(
        str(uuid4()),
        str(uuid4()),
    )

    assert job.status == JobStatus.FAILED
    assert job.error_message == "Workspace not found."
    assert job.finished_at is not None

    job_session.commit.assert_called()

    scanner_session.close.assert_called_once()
    job_session.close.assert_called_once()


def test_scan_workspace_task_success(monkeypatch):
    job_session = MagicMock()
    scanner_session = MagicMock()

    job = MagicMock()
    workspace = MagicMock()

    job.status = JobStatus.QUEUED

    # Calls to job_session.get():
    #
    # 1. Initial job lookup
    # 2. is_job_cancelling()
    # 3. update_job_progress()
    # 4. Final job lookup
    job_session.get.side_effect = [
        job,
        job,
        job,
        job,
    ]

    scanner_session.get.return_value = workspace

    service = MagicMock()

    result = {
        "files_found": 10,
        "new_files": 3,
        "unchanged_files": 4,
        "modified_files": 2,
        "duplicates": 1,
    }

    def fake_scan(_workspace, progress_callback):
        progress_callback(5, 10)
        return result

    service.scan.side_effect = fake_scan

    mock_session_local(
        monkeypatch,
        job_session,
        scanner_session,
    )

    monkeypatch.setattr(
        "backend.app.jobs.tasks.WorkspaceScanService",
        lambda session: service,
    )

    scan_workspace_task.run(
        str(uuid4()),
        str(uuid4()),
    )

    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100
    assert job.files_found == 10
    assert job.files_processed == 9
    assert job.total_files == 10
    assert job.duplicates == 1
    assert job.finished_at is not None
    assert job.started_at is not None

    assert job.files_processed == (
        result["new_files"]
        + result["unchanged_files"]
        + result["modified_files"]
    )

    scanner_session.commit.assert_called()
    job_session.commit.assert_called()

    scanner_session.close.assert_called_once()
    job_session.close.assert_called_once()


def test_scan_workspace_task_cancelled(monkeypatch):
    job_session = MagicMock()
    scanner_session = MagicMock()

    job = MagicMock()
    workspace = MagicMock()

    job.status = JobStatus.QUEUED

    # Calls:
    # 1. Initial job lookup
    # 2. is_job_cancelling() -> returns CANCELLING
    # 3. Final lookup in JobCancelled handler
    job_session.get.side_effect = [
        job,
        MagicMock(status=JobStatus.CANCELLING),
        job,
    ]

    scanner_session.get.return_value = workspace

    service = MagicMock()

    def fake_scan(_workspace, progress_callback):
        progress_callback(1, 10)

    service.scan.side_effect = fake_scan

    mock_session_local(
        monkeypatch,
        job_session,
        scanner_session,
    )

    monkeypatch.setattr(
        "backend.app.jobs.tasks.WorkspaceScanService",
        lambda session: service,
    )

    scan_workspace_task.run(
        str(uuid4()),
        str(uuid4()),
    )

    assert job.status == JobStatus.CANCELLED
    assert job.finished_at is not None

    scanner_session.rollback.assert_called_once()
    job_session.rollback.assert_called_once()
    job_session.commit.assert_called()

    scanner_session.close.assert_called_once()
    job_session.close.assert_called_once()


def test_scan_workspace_task_exception(monkeypatch):
    job_session = MagicMock()
    scanner_session = MagicMock()

    job = MagicMock()
    workspace = MagicMock()

    job.status = JobStatus.QUEUED

    # Calls:
    # 1. Initial job lookup
    # 2. Lookup inside Exception handler
    job_session.get.side_effect = [
        job,
        job,
    ]

    scanner_session.get.return_value = workspace

    service = MagicMock()
    service.scan.side_effect = RuntimeError("scanner exploded")

    mock_session_local(
        monkeypatch,
        job_session,
        scanner_session,
    )

    monkeypatch.setattr(
        "backend.app.jobs.tasks.WorkspaceScanService",
        lambda session: service,
    )

    with pytest.raises(RuntimeError, match="scanner exploded"):
        scan_workspace_task.run(
            str(uuid4()),
            str(uuid4()),
        )

    assert job.status == JobStatus.FAILED
    assert job.error_message == "scanner exploded"
    assert job.finished_at is not None

    scanner_session.rollback.assert_called_once()
    job_session.rollback.assert_called_once()
    job_session.commit.assert_called()

    scanner_session.close.assert_called_once()
    job_session.close.assert_called_once()
