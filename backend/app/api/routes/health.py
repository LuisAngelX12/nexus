from fastapi import APIRouter

router = APIRouter(
    prefix="",
    tags=["System"],
)


@router.get(
    "/health",
    summary="Health check",
    description="Returns the basic health status of the NEXUS API.",
)
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
    }