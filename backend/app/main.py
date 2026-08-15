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

from fastapi import FastAPI

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

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(activities.router, prefix="/api", tags=["activities"])
    app.include_router(leaderboard.router, prefix="/api", tags=["leaderboard"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])

    return app


app = create_app()
