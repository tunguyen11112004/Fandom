import re

from flask import has_app_context
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.extensions import db

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_COLUMN_EXTRAS = {
    "users": {"session_version": "INT NOT NULL DEFAULT 1"},
    "fandoms": {"is_active": "BOOLEAN NOT NULL DEFAULT TRUE"},
    "fan_submissions": {
        "fandom_id": "INT UNSIGNED NULL",
        "content_type": "VARCHAR(20) NOT NULL DEFAULT 'article'",
        "media_url": "VARCHAR(500) NULL",
        "source_url": "VARCHAR(500) NULL",
        "rights_confirmed": "BOOLEAN NOT NULL DEFAULT FALSE",
        "cover_image_url": "VARCHAR(500) NULL",
        "summary": "VARCHAR(500) NULL",
        "genre": "VARCHAR(60) NULL",
        "tags": "VARCHAR(255) NULL",
        "release_year": "INT NULL",
        "timeline_text": "TEXT NULL",
        "source_name": "VARCHAR(150) NULL",
        "updated_at": "DATETIME NULL",
    },
    "feedbacks": {
        "page_url": "VARCHAR(500) NULL",
        "reproduction_steps": "TEXT NULL",
        "browser_info": "VARCHAR(500) NULL",
        "is_deleted": "BOOLEAN NOT NULL DEFAULT FALSE",
        "deleted_by": "INT UNSIGNED NULL",
        "deleted_at": "DATETIME NULL",
    },
    "bookmarks": {"event_id": "INT UNSIGNED NULL"},
}

_EXTRA_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS user_sessions (
      session_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      user_id INT UNSIGNED NOT NULL,
      refresh_token_hash CHAR(64) NOT NULL,
      expires_at DATETIME NOT NULL,
      revoked_at DATETIME NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (session_id),
      UNIQUE KEY uq_user_sessions_hash (refresh_token_hash),
      KEY idx_user_sessions_user (user_id),
      CONSTRAINT fk_user_sessions_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
      notification_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      user_id INT UNSIGNED NOT NULL,
      title VARCHAR(200) NOT NULL,
      body TEXT NOT NULL,
      is_read BOOLEAN NOT NULL DEFAULT FALSE,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (notification_id),
      KEY idx_notifications_user (user_id),
      CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS user_dashboard_widgets (
      user_id INT UNSIGNED NOT NULL,
      widget_key VARCHAR(30) NOT NULL,
      is_visible BOOLEAN NOT NULL DEFAULT TRUE,
      sort_order INT NOT NULL DEFAULT 0,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (user_id, widget_key),
      CONSTRAINT fk_udw_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
]


def ensure_mysql_schema() -> None:
    if not settings.database_url.startswith("mysql"):
        raise RuntimeError("FanHubPlus uses MySQL. Set DATABASE_URL to a mysql+pymysql:// connection.")
    with engine.begin() as conn:
        for ddl in _EXTRA_TABLES:
            conn.execute(text(ddl))
        for table, columns in _COLUMN_EXTRAS.items():
            existing = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
                    ),
                    {"table": table},
                )
            }
            if not existing:
                continue
            if not re.fullmatch(r"[a-z_]+", table):
                continue
            for name, ddl in columns.items():
                if name not in existing and re.fullmatch(r"[a-z_]+", name) and re.fullmatch(r"[A-Za-z0-9_ ()',]+", ddl):
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def get_db():
    if has_app_context():
        return db.session
    return SessionLocal()


def close_db(_exc=None):
    return None
