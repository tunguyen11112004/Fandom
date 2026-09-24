from flask import Blueprint, request

from app.database import get_db
from app.deps import get_admin_user, get_optional_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Feedback
from app.schemas_extra import FeedbackIn, FeedbackUpdateIn
from app.serialize import log_activity, row_dict
from app.security import utcnow

bp = Blueprint("feedback", __name__)
bp.strict_slashes = False


@bp.post("/feedback")
def create_feedback():
    user = get_optional_user()
    db = get_db()
    body = parse_body(FeedbackIn)
    if body.type not in ("bug", "suggestion", "query"):
        raise AuthError(400, "invalid_type", "type phải là bug, suggestion hoặc query.")
    if user is None and not body.contact_email:
        raise AuthError(400, "email_required", "Visitor phải nhập email liên hệ.")
    row = Feedback(
        user_id=user.user_id if user else None,
        contact_email=str(body.contact_email) if body.contact_email else (user.email if user else None),
        type=body.type,
        subject=body.subject.strip(),
        message=body.message,
        page_url=body.page_url,
        reproduction_steps=body.reproduction_steps,
        browser_info=body.browser_info,
        status="new",
    )
    db.add(row)
    db.flush()
    log_activity(db, user.user_id if user else None, "submit_feedback", "feedback", row.feedback_id, body.type)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.get("/admin/feedback")
def admin_list_feedback():
    get_admin_user()
    db = get_db()
    q = db.query(Feedback).filter(Feedback.is_deleted.is_(False))
    ftype = request.args.get("type")
    if ftype:
        q = q.filter(Feedback.type == ftype)
    status = request.args.get("status")
    if status:
        q = q.filter(Feedback.status == status)
    rows = q.order_by(Feedback.created_at.desc()).all()
    return ok(data=[row_dict(r) for r in rows])


@bp.patch("/admin/feedback/<int:feedback_id>")
def admin_update_feedback(feedback_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Feedback, feedback_id)
    if row is None or row.is_deleted:
        raise AuthError(404, "not_found", "Không tìm thấy feedback.")
    body = parse_body(FeedbackUpdateIn)
    if body.status:
        if body.status not in ("new", "in_progress", "resolved", "closed"):
            raise AuthError(400, "invalid_status", "status không hợp lệ.")
        row.status = body.status
        if body.status in ("resolved", "closed"):
            row.resolved_at = utcnow()
    if body.admin_response is not None:
        row.admin_response = body.admin_response
    row.handled_by = admin.user_id
    log_activity(db, admin.user_id, "feedback_update", "feedback", feedback_id, row.status)
    db.commit()
    return ok(data=row_dict(row))


@bp.delete("/admin/feedback/<int:feedback_id>")
def admin_delete_feedback(feedback_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Feedback, feedback_id)
    if row is None:
        raise AuthError(404, "not_found", "Không tìm thấy feedback.")
    row.is_deleted = True
    row.deleted_by = admin.user_id
    row.deleted_at = utcnow()
    log_activity(db, admin.user_id, "feedback_delete", "feedback", feedback_id)
    db.commit()
    return ok(message="Đã ẩn feedback (soft delete).")
