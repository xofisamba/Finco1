"""Unhandled exception handler middleware for FincoGPT FastAPI app."""
import traceback
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging_config import get_logger, increment_errors

logger = get_logger("fincogpt.middleware.exception_handler")


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Catch all unhandled exceptions.

    - Logs full traceback at ERROR level
    - Increments total_errors metric
    - Returns a generic 500 response to the client (no internals leaked)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            increment_errors()

            # Log full traceback
            tb_str = traceback.format_exc()
            logger.error(
                "Unhandled exception: %s\n%s",
                str(exc),
                tb_str,
            )

            # Return generic 500 to client
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal error occurred. Please try again."},
            )
