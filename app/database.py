from flask import g
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _add_column(conn, table: str, column: str, ddl: str) -> None:
    cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
    if column not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_sqlite_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if "users" in tables:
            _add_column(conn, "users", "session_version", "session_version INTEGER NOT NULL DEFAULT 1")
        if "fandoms" in tables:
            _add_column(conn, "fandoms", "is_active", "is_active BOOLEAN NOT NULL DEFAULT 1")
        if "contents" in tables:
            _add_column(conn, "contents", "source_name", "source_name VARCHAR(150)")
            _add_column(conn, "contents", "source_url", "source_url VARCHAR(500)")
            _add_column(conn, "contents", "license_url", "license_url VARCHAR(500)")
            _add_column(conn, "contents", "rights_confirmed", "rights_confirmed BOOLEAN NOT NULL DEFAULT 0")
        if "fan_submissions" in tables:
            _add_column(conn, "fan_submissions", "content_type", "content_type VARCHAR(20) NOT NULL DEFAULT 'article'")
            _add_column(conn, "fan_submissions", "media_url", "media_url VARCHAR(500)")
            _add_column(conn, "fan_submissions", "source_url", "source_url VARCHAR(500)")
            _add_column(conn, "fan_submissions", "rights_confirmed", "rights_confirmed BOOLEAN NOT NULL DEFAULT 0")
            _add_column(conn, "fan_submissions", "fandom_id", "fandom_id INTEGER")
        if "feedbacks" in tables:
            _add_column(conn, "feedbacks", "page_url", "page_url VARCHAR(500)")
            _add_column(conn, "feedbacks", "reproduction_steps", "reproduction_steps TEXT")
            _add_column(conn, "feedbacks", "browser_info", "browser_info VARCHAR(500)")
            _add_column(conn, "feedbacks", "is_deleted", "is_deleted BOOLEAN NOT NULL DEFAULT 0")
            _add_column(conn, "feedbacks", "deleted_by", "deleted_by INTEGER")
            _add_column(conn, "feedbacks", "deleted_at", "deleted_at DATETIME")
        if "bookmarks" in tables:
            _add_column(conn, "bookmarks", "event_id", "event_id INTEGER")


def get_db():
    if "db" not in g:
        g.db = SessionLocal()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
