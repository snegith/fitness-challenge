"""
FastAPI application factory.

Responsibilities of this module:
    - Create the FastAPI app instance.
    - Mount all API routers.
    - Manage the application lifespan (startup / shutdown).
    - Start the scheduler via its single public entry point.

This module intentionally knows NOTHING about:
    - Scheduler job configuration
    - Cron trigger timing
    - Timezone setup for the scheduler
    - Which function the scheduled job calls

All of that lives exclusively in app.jobs.scheduler.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.db.init_db import init_db
from app.jobs.scheduler import start_scheduler
from app.routers import activities, auth, dashboard, leaderboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB and start scheduler on startup."""
    init_db()
    start_scheduler(app)
    yield
    # Scheduler shutdown is handled inside start_scheduler / the scheduler instance.


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Fitness Challenge API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Normalise Pydantic/FastAPI validation errors to the project's error envelope
    # {"error": "VALIDATION_ERROR", "message": "..."} (SRS §8, FR-7)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = []
        for error in exc.errors():
            loc = " → ".join(str(part) for part in error.get("loc", []) if part != "body")
            msg = error.get("msg", "")
            messages.append(f"{loc}: {msg}" if loc else msg)
        detail_msg = "; ".join(messages) if messages else "Invalid request payload."
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "VALIDATION_ERROR", "message": detail_msg},
        )

    # Normalise HTTPException detail dicts to the project's error envelope.
    # Routers raise HTTPException with detail={"error": ..., "message": ...}
    # which must be served as the top-level JSON body, not wrapped in {"detail": ...}.
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict):
            content = exc.detail
        else:
            content = {"error": "ERROR", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=content)

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(activities.router, prefix="/api", tags=["activities"])
    app.include_router(leaderboard.router, prefix="/api", tags=["leaderboard"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])

    return app


app = create_app()
