from fastapi import Request
from fastapi.responses import JSONResponse

from backend.app.schemas.error import ErrorResponse


def rate_limit_exceeded_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            detail="Rate limit exceeded. Try again later.",
        ).model_dump(),
    )
