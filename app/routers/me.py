from flask import Blueprint, request
from werkzeug.utils import secure_filename

from app.database import get_db
from app.deps import get_current_user
from app.errors import AuthError
from app.http_json import ok, parse_body, user_public
from app.models import (
    ActivityLog,
    Bookmark,
    Category,
    Content,
    Event,
    Fandom,
    Notification,
    UserCategory,
    UserDashboardWidget,
    UserFandom,
)
from app.schemas_extra import DashboardLayoutIn, FavoritesIn, ProfileIn
from app.serialize import row_dict

bp = Blueprint("me", __name__)
bp.strict_slashes = False
WIDGETS = ["activity", "favorites", "bookmarks", "recommendations", "events"]
AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _favorites(db, user_id):
    cats = [row_dict(c) for c in db.query(Category).join(UserCategory).filter(UserCategory.user_id == user_id).all()]
    fans = [row_dict(f) for f in db.query(Fandom).join(UserFandom).filter(UserFandom.user_id == user_id).all()]
    return {"categories": cats, "fandoms": fans}


@bp.get("/me")
def get_me():
    user = get_current_user()
    db = get_db()
    return ok(data={**user_public(user), "favorites": _favorites(db, user.user_id)})


@bp.post("/me/avatar")
def upload_avatar():
    user = get_current_user()
    file = request.files.get("file")
    if file is None or not file.filename:
        raise AuthError(400, "file_required", "Choose an avatar image.")
    if file.mimetype not in AVATAR_TYPES:
        raise AuthError(400, "invalid_file", "Only JPEG, PNG, or WebP is accepted.")
    data = file.read()
    if len(data) > 2 * 1024 * 1024:
        raise AuthError(400, "file_too_large", "Avatars must be 2MB or smaller.")
    from pathlib import Path

    folder = Path("uploads/avatars")
    folder.mkdir(parents=True, exist_ok=True)
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[file.mimetype]
    name = secure_filename(f"user-{user.user_id}{ext}")
    path = folder / name
    path.write_bytes(data)
    user.avatar_url = f"/uploads/avatars/{name}"
    get_db().commit()
    return ok(data=user_public(user))


@bp.get("/me/notifications")
def list_notifications():
    user = get_current_user()
    rows = get_db().query(Notification).filter(Notification.user_id == user.user_id).order_by(Notification.created_at.desc()).limit(50).all()
    return ok(data=[row_dict(r) for r in rows])


@bp.post("/me/notifications/<int:notification_id>/read")
def read_notification(notification_id: int):
    user = get_current_user()
    db = get_db()
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.user_id:
        raise AuthError(404, "not_found", "Notification not found.")
    row.is_read = True
    db.commit()
    return ok(data=row_dict(row))


@bp.patch("/me")
def patch_me():
    user = get_current_user()
    body = parse_body(ProfileIn)
    if body.name is not None:
        user.name = body.name.strip()
    if body.bio is not None:
        user.bio = body.bio
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.theme is not None:
        if body.theme not in ("light", "dark"):
            raise AuthError(400, "invalid_theme", "theme must be light or dark.")
        user.theme = body.theme
    if body.font_size is not None:
        if body.font_size not in ("small", "medium", "large"):
            raise AuthError(400, "invalid_font", "font_size must be small, medium, or large.")
        user.font_size = body.font_size
    get_db().commit()
    return ok(data=user_public(user))


@bp.put("/me/favorites")
def set_favorites():
    user = get_current_user()
    db = get_db()
    body = parse_body(FavoritesIn)
    if body.category_ids is not None:
        db.query(UserCategory).filter(UserCategory.user_id == user.user_id).delete()
        for cid in set(body.category_ids):
            if db.get(Category, cid):
                db.add(UserCategory(user_id=user.user_id, category_id=cid))
    if body.fandom_ids is not None:
        db.query(UserFandom).filter(UserFandom.user_id == user.user_id).delete()
        for fid in set(body.fandom_ids):
            fan = db.get(Fandom, fid)
            if fan and fan.is_active:
                db.add(UserFandom(user_id=user.user_id, fandom_id=fid))
    db.commit()
    return ok(data={**user_public(user), "favorites": _favorites(db, user.user_id)})


@bp.get("/me/dashboard")
def dashboard():
    user = get_current_user()
    db = get_db()
    hour = (user.last_login_at.hour if user.last_login_at else 9)
    if hour < 12:
        greet = "Good morning"
    elif hour < 18:
        greet = "Good afternoon"
    else:
        greet = "Good evening"
    cats = [row_dict(c) for c in db.query(Category).join(UserCategory).filter(UserCategory.user_id == user.user_id).all()]
    fans = [row_dict(f) for f in db.query(Fandom).join(UserFandom).filter(UserFandom.user_id == user.user_id).all()]
    logs = db.query(ActivityLog).filter(ActivityLog.user_id == user.user_id).order_by(ActivityLog.created_at.desc()).limit(10).all()
    bms = db.query(Bookmark).filter(Bookmark.user_id == user.user_id).order_by(Bookmark.created_at.desc()).limit(10).all()
    rec_q = db.query(Content).filter(Content.status == "published")
    if cats:
        rec_q = rec_q.filter(Content.category_id.in_([c["category_id"] for c in cats]))
    recs = rec_q.order_by(Content.created_at.desc()).limit(8).all()
    ev_ids = [b.event_id for b in bms if b.event_id]
    events = db.query(Event).filter(Event.event_id.in_(ev_ids)).all() if ev_ids else []
    widgets = db.query(UserDashboardWidget).filter(UserDashboardWidget.user_id == user.user_id).order_by(UserDashboardWidget.sort_order).all()
    if not widgets:
        widgets = [UserDashboardWidget(user_id=user.user_id, widget_key=k, is_visible=True, sort_order=i) for i, k in enumerate(WIDGETS)]
    return ok(
        data={
            "greeting": f"{greet}, {user.name}",
            "profile": user_public(user),
            "favorites": {"categories": cats, "fandoms": fans},
            "activity": [row_dict(a) for a in logs],
            "bookmarks": [row_dict(b) for b in bms],
            "recommendations": [row_dict(c) for c in recs],
            "events": [row_dict(e) for e in events],
            "layout": [row_dict(w) for w in widgets],
            "empty": not logs and not bms and not cats,
            "empty_hint": None if (logs or bms or cats) else "Pick favorite fandoms to personalize the dashboard (UC-04).",
        }
    )


@bp.put("/me/dashboard")
def set_dashboard():
    user = get_current_user()
    db = get_db()
    body = parse_body(DashboardLayoutIn)
    db.query(UserDashboardWidget).filter(UserDashboardWidget.user_id == user.user_id).delete()
    for i, w in enumerate(body.widgets):
        key = w.get("widget_key")
        if key not in WIDGETS:
            continue
        db.add(
            UserDashboardWidget(
                user_id=user.user_id,
                widget_key=key,
                is_visible=bool(w.get("is_visible", True)),
                sort_order=int(w.get("sort_order", i)),
            )
        )
    db.commit()
    rows = db.query(UserDashboardWidget).filter(UserDashboardWidget.user_id == user.user_id).order_by(UserDashboardWidget.sort_order).all()
    return ok(data=[row_dict(r) for r in rows])
