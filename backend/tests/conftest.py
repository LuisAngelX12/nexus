from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.models.base import Base

settings = get_settings()

test_engine = create_engine(
    settings.test_database_url,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture
def session() -> Generator[Session]:
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            session.rollback()

    Base.metadata.drop_all(bind=test_engine)
