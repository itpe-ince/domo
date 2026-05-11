import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


class ApiError(HTTPException):
    """Domo standard API error following design.md §3.1 spec."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict | None = None,
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.code = code
        self.error_message = message
        self.details = details or {}
        super().__init__(status_code=http_status, detail=message)


def _error_response(http_status: int, code: str, message: str, details: dict | None = None):
    return JSONResponse(
        status_code=http_status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return _error_response(exc.status_code, exc.code, exc.error_message, exc.details)

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException):
        code = "INTERNAL_ERROR"
        if exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 422:
            code = "VALIDATION_ERROR"
        return _error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_exc_handler(request: Request, exc: Exception):
        log.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return _error_response(
            500,
            "INTERNAL_ERROR",
            "Internal server error. Please contact support if this persists.",
        )
