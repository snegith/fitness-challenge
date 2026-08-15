"""
Database engine and session factory.

- Engine is created from settings.db_path (SQLite file path).
- WAL mode is intentionally NOT enabled (approved decision — revisit only if a
  real concurrency issue is observed, not preemptively).
- Foreign-key enforcement is activated via a connect event because SQLite disables
  it by default.
- SessionLocal is a plain SQLAlchemy sessionmaker; use get_db() as a FastAPI
  dependency to obtain a per-request session.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings

DATABASE_URL = f"sqlite:///{settings.db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enforce_foreign_keys(dbapi_connection, _connection_record):
    """Enable foreign-key constraints for every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session and closes it afterwards.

    Usage:
        @router.get("/something")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
