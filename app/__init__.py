import secrets
import time

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from markupsafe import Markup
from flask_cors import CORS

from app.config import settings
from app.database import close_db, ensure_mysql_schema
from app.errors import AuthError
from app.extensions import db
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
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    from . import models  # noqa: F401
    from .account import bp as account_bp
    from .account import current_user
    from .routes import bp as pages_bp
    from .seed import seed_catalog_if_empty, seed_demo_users, seed_detail_gaps, seed_reference_data, seed_showcase_if_empty
    from .services_auth import seed_admin

    app.register_blueprint(pages_bp)
    app.register_blueprint(account_bp)

    for blueprint in (
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
        if blueprint is auth_bp:
            app.register_blueprint(blueprint, url_prefix=f"{PUBLIC_PREFIX}/auth")
        else:
            app.register_blueprint(blueprint, url_prefix=PUBLIC_PREFIX)

    @app.before_request
    def guard_form_post():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        if request.path.startswith("/api/"):
            return None
        expected = session.get("csrf") or ""
        sent = request.form.get("csrf") or request.headers.get("X-CSRF-Token") or ""
        if expected and sent and secrets.compare_digest(sent, expected):
            return None
        if request.is_json or request.path.startswith("/support/"):
            return jsonify(ok=False, error="The form expired. Refresh and try again."), 400
        return "The form expired. Go back, refresh, and try again.", 400

    @app.before_request
    def slow_repeat_posts():
        if request.method != "POST":
            return None
        if request.path.startswith("/api/") or request.path.startswith("/support/"):
            return None
        if request.path in {"/logout", "/display"}:
            return None
        now = time.time()
        stamps = session.get("post_stamps") or {}
        stamps = {key: stamp for key, stamp in stamps.items() if now - float(stamp) < 30}
        last = float(stamps.get(request.path, 0) or 0)
        if last and now - last < 3:
            session["notice"] = "Please wait a moment before sending that again."
            back = request.referrer if request.referrer and request.referrer.startswith(request.host_url) else url_for("main.home")
            return redirect(back)
        stamps[request.path] = now
        session["post_stamps"] = stamps
        return None

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.template_filter("rich")
    def rich_filter(value):
        from .account import _clean_html

        cleaned = _clean_html(value or "")
        if cleaned and "<" not in cleaned:
            cleaned = "<p>" + cleaned.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
        return Markup(cleaned) if cleaned else Markup("")

    @app.context_processor
    def inject_user():
        from .models import Category, Event

        user = current_user()
        notice = session.pop("notice", None)
        if user is not None:
            display = {"theme": user.theme or "dark", "font": user.font_size or "medium"}
        else:
            display = {
                "theme": session.get("theme", "dark"),
                "font": session.get("font", "medium"),
            }
        token = session.get("csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf"] = token
        return {
            "current_user": user,
            "csrf_token": token,
            "site_notice": notice,
            "display": display,
            "nav_categories": Category.query.order_by(Category.category_id).all(),
            "events": Event.query.order_by(Event.start_at.asc()).limit(8).all(),
        }

    @app.errorhandler(AuthError)
    def handle_auth_error(exc: AuthError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(404)
    def handle_404(_e):
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": f"No route for {request.method} {request.path}",
                        "try": ["/health", "/sitemap", PUBLIC_PREFIX],
                    }
                ),
                404,
            )
        return render_template("404.html"), 404

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "db": "mysql"})

    @app.get("/api")
    def api_index():
        return jsonify({"ok": True, "name": settings.app_name, "groups": API_GROUPS, "auth": AUTH_CATALOG})

    @app.get("/uploads/avatars/<path:filename>")
    def avatar_file(filename: str):
        from pathlib import Path

        from flask import send_from_directory

        folder = Path("uploads/avatars").resolve()
        return send_from_directory(folder, filename)

    app.teardown_appcontext(close_db)

    with app.app_context():
        ensure_mysql_schema()
        seed_admin(db.session)
        seed_reference_data(db.session)
        seed_catalog_if_empty(db.session)
        seed_showcase_if_empty(db.session)
        seed_detail_gaps(db.session)
        seed_demo_users(db.session)

    return app
