"""Request logging middleware for FincoGPT FastAPI app."""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging_config import get_logger, increment_requests, increment_errors

logger = get_logger("fincogpt.middleware.request_logger")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every incoming HTTP request: method, path, client IP, status, duration_ms.

    Also increments the process-global request counter.
    Errors are counted separately by the exception handler.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Record start time
        t0 = time.monotonic()

        # Extract client IP (handles X-Forwarded-For behind nginx)
        client_ip = request.headers.get("X-Forwarded-For", "")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        method = request.method
        path = request.url.path

        # Increment request counter
        increment_requests()

        # Dispatch request
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            increment_errors()
            raise

        duration_ms = round((time.monotonic() - t0) * 1000, 2)

        # Log at appropriate level
        log_level = logger.info if status < 400 else logger.warning if status < 500 else logger.error
        log_level(
            "method=%-6s path=%-60s client=%-15s status=%-3s duration_ms=%s",
            method,
            path,
            client_ip,
            status,
            duration_ms,
        )

        return response
