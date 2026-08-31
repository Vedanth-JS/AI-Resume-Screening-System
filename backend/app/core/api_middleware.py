"""
Enterprise API Middleware — Global exception handlers, request logging, response timing.
Standardizes error responses, adds correlation IDs, and logs all requests.
"""
import time
import uuid
import traceback
from typing import Callable
from fastapi import Request, Response, FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from ..core.logger import log
from ..services.auth_service import AuthError


# ─── Request ID Middleware ─────────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-ID into every request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        request.state.start_time = time.time()

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{(time.time() - request.state.start_time) * 1000:.0f}ms"
        return response


# ─── Request Logging Middleware ────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every API request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # Skip logging for health/ping endpoints
        if not any(
            request.url.path.startswith(p)
            for p in ("/health", "/api/health", "/db/ping", "/metrics", "/docs", "/redoc", "/openapi")
        ):
            log.info(
                "api_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
                client=request.client.host if request.client else None,
            )

        return response


# ─── Global Exception Handlers ─────────────────────────────────────────────────

def _add_cors_headers(request: Request, response: Response) -> Response:
    """Manually add CORS headers to exception responses since they bypass CORSMiddleware."""
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-API-Key, X-Device-Name, X-CSRF-Token"
    return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError):
        """Handle custom AuthError from auth_service."""
        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "auth_error",
                "message": str(exc),
                "detail": exc.extra or {},
                "request_id": getattr(request.state, "request_id", None),
            },
            headers=exc.extra if isinstance(exc.extra, dict) else None,
        )
        return _add_cors_headers(request, response)

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors with clean formatting."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " → ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        response = JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "errors": errors,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _add_cors_headers(request, response)

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError (e.g., invalid UUID, bad enum)."""
        response = JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _add_cors_headers(request, response)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        response = JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": f"Resource not found: {request.url.path}",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _add_cors_headers(request, response)

    @app.exception_handler(429)
    async def rate_limit_handler(request: Request, exc):
        response = JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "message": "Too many requests. Please try again later.",
                "retry_after": "60",
                "request_id": getattr(request.state, "request_id", None),
            },
            headers={"Retry-After": "60"},
        )
        return _add_cors_headers(request, response)

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        """Catch-all for unhandled exceptions. Logs traceback, returns generic message."""
        tb = traceback.format_exc()
        log.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            traceback=tb[-1000:],  # last 1000 chars
        )
        response = JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred. The incident has been logged.",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _add_cors_headers(request, response)
