import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _ensure_columns():
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    wanted = {
        "users": {
            "interests": "VARCHAR(240) NOT NULL DEFAULT ''",
            "theme": "VARCHAR(20) NOT NULL DEFAULT 'dark'",
            "font_size": "VARCHAR(20) NOT NULL DEFAULT 'medium'",
            "avatar_path": "VARCHAR(200) NOT NULL DEFAULT ''",
            "last_seen": "DATETIME",
        },
        "contents": {
            "view_count": "INTEGER NOT NULL DEFAULT 0",
            "published": "BOOLEAN NOT NULL DEFAULT 1",
            "featured": "BOOLEAN NOT NULL DEFAULT 0",
            "tags": "VARCHAR(200) NOT NULL DEFAULT ''",
            "embed_url": "VARCHAR(300) NOT NULL DEFAULT ''",
        },
    }
    for table, columns in wanted.items():
        if table not in inspector.get_table_names():
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in present:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
    db.session.commit()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-fan-hub-plus")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        app.instance_path, "fanhub.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from . import models  # noqa: F401
    from .account import bp as account_bp
    from .account import current_user
    from .routes import bp

    app.register_blueprint(bp)
    app.register_blueprint(account_bp)

    @app.context_processor
    def inject_user():
        from .events import EVENTS
        from .models import Category

        user = current_user()
        if user is not None:
            display = {"theme": user.theme or "dark", "font": user.font_size or "medium"}
        else:
            from flask import session

            display = {
                "theme": session.get("theme", "dark"),
                "font": session.get("font", "medium"),
            }
        return {
            "current_user": user,
            "display": display,
            "nav_categories": Category.query.order_by(Category.id).all(),
            "events": EVENTS,
        }

    with app.app_context():
        db.create_all()
        _ensure_columns()
        from .seed import seed_if_empty, seed_users

        seed_if_empty()
        seed_users()

    return app
