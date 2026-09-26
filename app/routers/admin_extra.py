from flask import Blueprint, request
from sqlalchemy import func

from app.database import get_db
from app.deps import get_admin_user
from app.errors import AuthError
from app.http_json import ok, parse_body, user_public
from app.models import (
    ActivityLog,
    Bookmark,
    Category,
    ChatbotQuery,
    Content,
    ContentRating,
    Event,
    FanSubmission,
    Feedback,
    MerchandiseItem,
    User,
)
from app.schemas_extra import UserAdminUpdateIn
from app.serialize import log_activity, page_args, paginate, row_dict
from app.security import like_contains, utcnow
from datetime import datetime


bp = Blueprint("admin_extra", __name__)
bp.strict_slashes = False


def _range():
    start = request.args.get("from")
    end = request.args.get("to")
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None
    return start_dt, end_dt


@bp.get("/admin/users")
def list_users():
    get_admin_user()
    db = get_db()
    q = db.query(User)
    role = request.args.get("role")
    if role:
        q = q.filter(User.role == role)
    search = request.args.get("q")
    if search:
        like = like_contains(search)
        q = q.filter((User.email.ilike(like)) | (User.name.ilike(like)))
    q = q.order_by(User.created_at.desc())
    page, page_size = page_args()
    items, meta = paginate(q, page, page_size)
    out = []
    for u in items:
        subs = db.query(FanSubmission).filter(FanSubmission.user_id == u.user_id).count()
        out.append({**user_public(u), "submission_count": subs})
    return ok(data={"items": out, "meta": meta})


@bp.patch("/admin/users/<int:user_id>")
def update_user(user_id: int):
    admin = get_admin_user()
    if admin.user_id == user_id:
        raise AuthError(400, "self_forbidden", "You cannot lock or delete your own account.")
    db = get_db()
    row = db.get(User, user_id)
    if row is None:
        raise AuthError(404, "not_found", "User not found.")
    body = parse_body(UserAdminUpdateIn)
    if body.name is not None:
        row.name = body.name
    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise AuthError(400, "invalid_role", "role must be user or admin.")
        row.role = body.role
    if body.is_active is not None:
        row.is_active = body.is_active
        if not body.is_active:
            row.session_version = (row.session_version or 1) + 1
    log_activity(db, admin.user_id, "user_update", "user", user_id)
    db.commit()
    return ok(data=user_public(row))


@bp.post("/admin/users/<int:user_id>/lock")
def lock_user(user_id: int):
    admin = get_admin_user()
    if admin.user_id == user_id:
        raise AuthError(400, "self_forbidden", "You cannot lock your own account.")
    db = get_db()
    row = db.get(User, user_id)
    if row is None:
        raise AuthError(404, "not_found", "User not found.")
    row.is_active = False
    row.session_version = (row.session_version or 1) + 1
    log_activity(db, admin.user_id, "user_deactivate", "user", user_id, "sessions revoked")
    db.commit()
    return ok(data=user_public(row), message="Account locked.")


@bp.post("/admin/users/<int:user_id>/unlock")
def unlock_user(user_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(User, user_id)
    if row is None:
        raise AuthError(404, "not_found", "User not found.")
    row.is_active = True
    log_activity(db, admin.user_id, "user_activate", "user", user_id)
    db.commit()
    return ok(data=user_public(row), message="Account unlocked.")


@bp.get("/admin/reports/overview")
def report_overview():
    get_admin_user()
    db = get_db()
    start, end = _range()
    active_q = db.query(User).filter(User.is_active.is_(True))
    if start:
        active_q = active_q.filter(User.last_login_at >= start)
    if end:
        active_q = active_q.filter(User.last_login_at <= end)
    return ok(
        data={
            "users": db.query(User).count(),
            "active_users": active_q.count(),
            "contents": db.query(Content).count(),
            "published_contents": db.query(Content).filter(Content.status == "published").count(),
            "events": db.query(Event).count(),
            "merchandise": db.query(MerchandiseItem).count(),
            "bookmarks": db.query(Bookmark).count(),
            "ratings": db.query(ContentRating).count(),
            "submissions_pending": db.query(FanSubmission).filter(FanSubmission.status == "pending").count(),
            "feedback_open": db.query(Feedback).filter(Feedback.is_deleted.is_(False), Feedback.status.in_(["new", "in_progress"])).count(),
            "content_views": db.query(func.coalesce(func.sum(Content.view_count), 0)).scalar(),
            "merchandise_views": db.query(func.coalesce(func.sum(MerchandiseItem.view_count), 0)).scalar(),
            "chat_messages": db.query(ChatbotQuery).count(),
            "range": {"from": start.isoformat() if start else None, "to": end.isoformat() if end else None},
        }
    )


@bp.get("/admin/reports/user-growth")
def report_users():
    get_admin_user()
    db = get_db()
    rows = db.query(func.date(User.created_at), func.count(User.user_id)).group_by(func.date(User.created_at)).all()
    return ok(data=[{"date": str(d), "count": c} for d, c in rows])


@bp.get("/admin/reports/content-performance")
def report_content():
    get_admin_user()
    db = get_db()
    rows = (
        db.query(Content)
        .filter(Content.status == "published")
        .order_by(Content.view_count.desc(), Content.popularity_score.desc())
        .limit(50)
        .all()
    )
    return ok(data=[row_dict(r) for r in rows])


@bp.get("/admin/reports/category-performance")
def report_category():
    get_admin_user()
    db = get_db()
    rows = (
        db.query(Category.category_id, Category.name, func.count(Content.content_id), func.coalesce(func.sum(Content.view_count), 0))
        .outerjoin(Content, Content.category_id == Category.category_id)
        .group_by(Category.category_id, Category.name)
        .all()
    )
    return ok(data=[{"category_id": i, "name": n, "content_count": c, "total_views": int(v)} for i, n, c, v in rows])


@bp.get("/admin/reports/engagement")
def report_engagement():
    get_admin_user()
    db = get_db()
    return ok(
        data={
            "logins": db.query(ActivityLog).filter(ActivityLog.action == "login").count(),
            "views": db.query(ActivityLog).filter(ActivityLog.action == "view").count(),
            "ratings": db.query(ContentRating).count(),
            "bookmarks": db.query(Bookmark).count(),
            "chat_messages": db.query(ChatbotQuery).count(),
        }
    )


@bp.get("/admin/reports/submissions-feedback")
def report_sub_fb():
    get_admin_user()
    db = get_db()
    return ok(
        data={
            "submissions": {
                "pending": db.query(FanSubmission).filter(FanSubmission.status == "pending").count(),
                "approved": db.query(FanSubmission).filter(FanSubmission.status == "approved").count(),
                "rejected": db.query(FanSubmission).filter(FanSubmission.status == "rejected").count(),
            },
            "feedback": {
                "new": db.query(Feedback).filter(Feedback.is_deleted.is_(False), Feedback.status == "new").count(),
                "in_progress": db.query(Feedback).filter(Feedback.is_deleted.is_(False), Feedback.status == "in_progress").count(),
                "resolved": db.query(Feedback).filter(Feedback.is_deleted.is_(False), Feedback.status == "resolved").count(),
                "closed": db.query(Feedback).filter(Feedback.is_deleted.is_(False), Feedback.status == "closed").count(),
            },
        }
    )


@bp.get("/admin/reports/merchandise-media")
def report_merch():
    get_admin_user()
    rows = get_db().query(MerchandiseItem).order_by(MerchandiseItem.view_count.desc()).limit(50).all()
    return ok(data=[row_dict(r, extra={"buyable": False}) for r in rows])


@bp.get("/admin/reports/chatbot-unanswered")
def report_unanswered():
    get_admin_user()
    rows = (
        get_db()
        .query(ChatbotQuery)
        .filter(ChatbotQuery.matched_faq_id.is_(None))
        .order_by(ChatbotQuery.created_at.desc())
        .limit(100)
        .all()
    )
    return ok(data=[row_dict(r) for r in rows])

