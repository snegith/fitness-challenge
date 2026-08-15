"""
Database initialisation — creates all tables on first run.

Uses SQLAlchemy metadata.create_all(), which is a no-op if the tables already
exist (safe to call at every startup).

No migration tooling (Alembic) is used at this scale.  If the schema must change,
drop the SQLite file and let this recreate it.  There is no production data at risk
for this assignment.
"""

from app.db.database import engine
from app.db.models import Base


def init_db() -> None:
    """Create all tables defined in models.py if they do not already exist."""
    Base.metadata.create_all(bind=engine)
