import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(
            "X-Request-ID",
            str(uuid4()),
        )

        request.state.request_id = request_id

        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration * 1000,
        )

        return response
