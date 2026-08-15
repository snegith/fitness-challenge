"""
Shared pytest fixtures for backend tests.

Fixtures provided:
    db_session   – an in-memory SQLite session with all tables created;
                   closed and torn down after each test for isolation.
    client       – a FastAPI TestClient wired to the in-memory DB.

The in-memory DB is separate from the application's configured DB_PATH so tests
never touch a real database file.

FK enforcement is explicitly enabled on the in-memory engine via a connect event,
mirroring the production engine setup in app.db.database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import get_db
from app.db.models import Base
from app.main import app

# In-memory SQLite with StaticPool — all connections share the same database,
# preventing "no such table" errors when async code opens a new connection.
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a clean in-memory database session for each test.
    All tables are created fresh; FK enforcement is on; session is closed after.

    StaticPool ensures every SQLAlchemy connection checkout reuses the single
    in-memory connection, so tables created by create_all() are visible to all
    queries issued through the same engine — including those dispatched from
    async FastAPI handler contexts.
    """
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Mirror the FK-enforcement listener from app.db.database
    @event.listens_for(test_engine, "connect")
    def _enforce_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    """
    FastAPI TestClient with the in-memory DB injected via dependency override.
    The scheduler is not started in tests.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
