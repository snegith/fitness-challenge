"""
Shared pytest fixtures for backend tests.

Fixtures provided:
    db_session   – an in-memory SQLite session with all tables created;
                   rolled back after each test for isolation.
    client       – a FastAPI TestClient wired to the in-memory DB.
    seeded_users – pre-inserted user rows for tests that need existing data.

The in-memory DB is separate from the application's configured DB_PATH so tests
never touch a real database file.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import get_db
from app.db.models import Base
from app.main import app

# In-memory SQLite — isolated per test session
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a clean in-memory database session for each test.
    All tables are created fresh; the session is closed after the test.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


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
