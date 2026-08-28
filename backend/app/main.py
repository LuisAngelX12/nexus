from fastapi import FastAPI

from backend.app.api.v1.auth import router as auth_router


app = FastAPI(
    title="NEXUS API",
    version="0.1.0",
)


app.include_router(
    auth_router,
    prefix="/api/v1",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}