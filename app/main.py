from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from app.config import settings
from app.database import Base, SessionLocal, close_db, engine, ensure_sqlite_schema
from app.errors import AuthError
from app.routers.admin_extra import bp as admin_extra_bp
from app.routers.auth import AUTH_CATALOG, bp as auth_bp
from app.routers.bookmarks import bp as bookmarks_bp
from app.routers.catalog import bp as catalog_bp
from app.routers.characters import bp as characters_bp
from app.routers.chat import bp as chat_bp
from app.routers.contents import bp as contents_bp
from app.routers.events import bp as events_bp
from app.routers.feedback import bp as feedback_bp
from app.routers.me import bp as me_bp
from app.routers.merchandise import bp as merch_bp
from app.routers.submissions import bp as submissions_bp
from app.seed import seed_reference_data
from app.services_auth import seed_admin

import app.models  # noqa: F401  — register ORM tables


PUBLIC_PREFIX = settings.api_prefix

API_GROUPS = {
    "auth": f"{PUBLIC_PREFIX}/auth",
    "me": f"{PUBLIC_PREFIX}/me",
    "catalog": f"{PUBLIC_PREFIX}/categories",
    "contents": f"{PUBLIC_PREFIX}/contents",
    "characters": f"{PUBLIC_PREFIX}/characters",
    "merchandise": f"{PUBLIC_PREFIX}/merchandise",
    "events": f"{PUBLIC_PREFIX}/events",
    "bookmarks": f"{PUBLIC_PREFIX}/bookmarks",
    "submissions": f"{PUBLIC_PREFIX}/submissions",
    "feedback": f"{PUBLIC_PREFIX}/feedback",
    "chat": f"{PUBLIC_PREFIX}/chat",
    "admin": f"{PUBLIC_PREFIX}/admin",
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()

    db = SessionLocal()
    try:
        seed_admin(db)
        seed_reference_data(db)
    finally:
        db.close()

    app.teardown_appcontext(close_db)

    @app.errorhandler(AuthError)
    def handle_auth_error(exc: AuthError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(404)
    def handle_404(_e):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "not_found",
                    "message": f"Không có route {request.method} {request.path}",
                    "try": ["/", "/health", "/sitemap", "/auth-ui", PUBLIC_PREFIX],
                }
            ),
            404,
        )

    for bp in (
        auth_bp,
        me_bp,
        catalog_bp,
        contents_bp,
        characters_bp,
        merch_bp,
        events_bp,
        bookmarks_bp,
        submissions_bp,
        feedback_bp,
        chat_bp,
        admin_extra_bp,
    ):
        if bp is auth_bp:
            app.register_blueprint(bp, url_prefix=f"{PUBLIC_PREFIX}/auth")
        else:
            app.register_blueprint(bp, url_prefix=PUBLIC_PREFIX)

    @app.get("/")
    def root():
        return jsonify(
            {
                "ok": True,
                "name": settings.app_name,
                "health": "/health",
                "sitemap": "/sitemap",
                "auth_ui": "/auth-ui",
                "groups": API_GROUPS,
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "db": settings.database_url.split("://")[0]})

    @app.get("/sitemap")
    def sitemap():
        return jsonify(
            {
                "ok": True,
                "pages": [
                    {"role": "visitor", "items": ["Home", "Categories", "Explorer", "Content detail", "Characters", "Merchandise", "Events", "Feedback", "Chat FAQ", "Login", "Register"]},
                    {"role": "member", "items": ["Dashboard", "Bookmarks", "Ratings", "Favorites", "Fan submit", "Profile/theme"]},
                    {"role": "admin", "items": ["CRUD catalog/content/character/merch/event", "Moderation", "Users", "Feedback", "Reports", "FAQ"]},
                ],
                "api": API_GROUPS,
                "auth": AUTH_CATALOG,
            }
        )

    @app.get("/auth-ui")
    def auth_ui():
        return render_template("auth_ui.html", api_prefix=settings.api_prefix)

    @app.get("/uploads/avatars/<path:filename>")
    def avatar_file(filename: str):
        from flask import send_from_directory
        from pathlib import Path

        folder = Path("uploads/avatars").resolve()
        return send_from_directory(folder, filename)

    @app.get("/favicon.ico")
    def favicon():
        return ("", 204)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
