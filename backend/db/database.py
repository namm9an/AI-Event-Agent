"""
AI Event Agent — Database Connection & Session Management

Creates the SQLite engine, session factory, and init function.
"""

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import APP_TIMEZONE, DATABASE_URL, DEFAULT_REPORT_TIME, DEFAULT_SCRAPE_TIME, logger
from db.models import Base


# Create engine — SQLite with check_same_thread=False for FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
    logger.info("Added missing column %s.%s", table, column)


def _sqlite_safe_migrations() -> None:
    """Perform additive migrations for existing SQLite databases."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "speakers" in tables:
        _add_column_if_missing("speakers", "linkedin_url", "VARCHAR(2000) DEFAULT ''")
        _add_column_if_missing("speakers", "linkedin_bio", "TEXT DEFAULT ''")
        _add_column_if_missing("speakers", "topic_links", "JSON")
        _add_column_if_missing("speakers", "topic_category", "VARCHAR(200) DEFAULT ''")
        _add_column_if_missing("speakers", "previous_talks", "JSON")
        _add_column_if_missing("speakers", "wikipedia_url", "VARCHAR(2000) DEFAULT ''")


def _seed_defaults() -> None:
    """Seed initial admin queries and schedule defaults."""
    from db.models import AppSetting, SearchQuery

    db = SessionLocal()
    try:
        defaults = {
            "timezone": APP_TIMEZONE,
            "scrape_time": DEFAULT_SCRAPE_TIME,
            "report_time": DEFAULT_REPORT_TIME,
        }
        for key, value in defaults.items():
            if not db.query(AppSetting).filter(AppSetting.key == key).first():
                db.add(AppSetting(key=key, value=value))

        if db.query(SearchQuery).count() == 0:
            seed_queries = [
                ("AI ML conference India 2025 2026", "AI/ML", 10),
                ("upcoming AI events India", "AI/ML", 20),
                ("machine learning meetup India 2025 2026", "AI/ML", 30),
                ("cloud computing summit India 2025 2026", "Cloud", 40),
                ("GPU infrastructure summit India 2025 2026", "GPU Infra", 50),
                ("frontier model conference India 2025 2026", "Frontier Models", 60),
            ]
            for i, (query, topic, priority) in enumerate(seed_queries, start=1):
                db.add(
                    SearchQuery(
                        id=f"seed-query-{i}",
                        query=query,
                        topic=topic,
                        is_active=True,
                        priority=priority,
                    )
                )
        db.commit()
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    _sqlite_safe_migrations()
    _seed_defaults()
    logger.info("Database initialized: %s", DATABASE_URL)


def get_db():
    """
    FastAPI dependency — yields a database session
    and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
