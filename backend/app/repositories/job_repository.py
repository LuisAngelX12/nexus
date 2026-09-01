from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.job import Job


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(
        self,
        job_id: UUID,
    ) -> Job | None:
        statement = select(Job).where(
            Job.id == job_id,
        )

        return self.session.scalar(statement)

    def create(
        self,
        job: Job,
    ) -> Job:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)

        return job
