from fastapi import FastAPI

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.ready import router as ready_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.files import router as files_router
from backend.app.api.v1.jobs import (
    router as jobs_router,
)
from backend.app.api.v1.workspaces import (
    router as workspaces_router,
)
from backend.app.core.logging_config import configure_logging
from backend.app.middleware.request_id import (
    RequestIDMiddleware,
)

configure_logging()

app = FastAPI(
    title="NEXUS API",
    description="""
    # NEXUS

    NEXUS is a secure asynchronous system for filesystem
    analysis and workspace management.

    ## Main features

    - User authentication
    - Workspace management
    - Secure filesystem scanning
    - Asynchronous scan jobs
    - Job progress tracking
    - Job cancellation
    - File discovery
    - PostgreSQL persistence
    - Redis + Celery workers

    ## Architecture

    NEXUS is designed as a modular backend using:

    - FastAPI
    - PostgreSQL
    - Redis
    - Celery
    - SQLAlchemy
    - Alembic
    """,
    version="1.0.0",
    contact={
        "name": "NEXUS Project",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    RequestIDMiddleware,
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    files_router,
    prefix="/api/v1",
)

app.include_router(
    workspaces_router,
    prefix="/api/v1",
)

app.include_router(
    jobs_router,
    prefix="/api/v1",
)

app.include_router(health_router)

app.include_router(ready_router)