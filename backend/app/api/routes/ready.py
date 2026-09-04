from fastapi import APIRouter

router = APIRouter(
    prefix="",
    tags=["System"],
)


@router.get(
    "/ready",
    summary="Readiness check",
    description=("Checks whether the NEXUS API is ready to process requests."),
)
async def readiness_check() -> dict[str, str]:
    return {
        "status": "ready",
    }
