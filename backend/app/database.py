from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables on startup, then run lightweight column migrations."""
    from app.models import source, news_item, favorite, broadcast_log, user  # noqa
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def _run_migrations():
    """
    Idempotent ALTER TABLE migrations for columns that need widening.
    Runs on every startup; Postgres silently no-ops if the column is already TEXT.
    """
    migrations = [
        # Widen VARCHAR(500) → TEXT  (arXiv titles exceed 500 chars)
        "ALTER TABLE news_items ALTER COLUMN title TYPE TEXT",
        # Widen other varchar columns that could be hit by long URLs / authors
        "ALTER TABLE news_items ALTER COLUMN url TYPE TEXT",
        "ALTER TABLE news_items ALTER COLUMN author TYPE TEXT",
        "ALTER TABLE news_items ALTER COLUMN image_url TYPE TEXT",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()   # Column may already be TEXT — safe to ignore