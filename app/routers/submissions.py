from flask import Blueprint

from app.database import get_db
from app.deps import get_admin_user, get_current_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Category, Content, Fandom, FanSubmission, ModerationLog, Notification, Tag, User
from app.emailer import send_moderation_email
from app.schemas_extra import ReviewIn, SubmissionIn
from app.serialize import log_activity, row_dict, slugify
from app.security import utcnow

bp = Blueprint("submissions", __name__)
bp.strict_slashes = False


def _notify_owner(db, user_id: int, title: str, decision: str, reason: str | None = None) -> None:
    owner = db.get(User, user_id)
    if owner is None:
        return
    send_moderation_email(owner.email, title, decision, reason)
    db.add(
        Notification(
            user_id=user_id,
            title=f"Moderation: {title}",
            body=f"The piece was {decision}." + (f" Reason: {reason}" if reason else ""),
        )
    )


@bp.get("/submissions")
def my_submissions():
    user = get_current_user()
    rows = get_db().query(FanSubmission).filter(FanSubmission.user_id == user.user_id).order_by(FanSubmission.created_at.desc()).all()
    return ok(data=[row_dict(r) for r in rows])


@bp.post("/submissions")
def submit():
    user = get_current_user()
    db = get_db()
    body = parse_body(SubmissionIn)
    if not body.rights_confirmed:
        raise AuthError(400, "rights_required", "You must confirm you have the right to share this.")
    if db.get(Category, body.category_id) is None:
        raise AuthError(400, "not_found", "Category not found.")
    if body.fandom_id:
        fan = db.get(Fandom, body.fandom_id)
        if fan is None or not fan.is_active:
            raise AuthError(400, "not_found", "Fandom not found.")
    if body.content_type not in ("article", "video", "audio", "image", "trailer", "explainer"):
        raise AuthError(400, "invalid_type", "That content type is not valid.")
    from app.account import _post_wait

    wait = _post_wait(user)
    if wait:
        raise AuthError(429, "rate_limited", f"You can send 10 pieces every 12 hours. Try again in {wait}.")
    row = FanSubmission(
        user_id=user.user_id,
        category_id=body.category_id,
        fandom_id=body.fandom_id,
        content_type=body.content_type,
        title=body.title.strip(),
        body=body.body,
        media_url=body.media_url,
        source_url=body.source_url,
        cover_image_url=body.cover_image_url,
        rights_confirmed=True,
        status="pending",
    )
    from app.security import utcnow

    row.created_at = utcnow()
    db.add(row)
    db.flush()
    log_activity(db, user.user_id, "submit_content", "submission", row.submission_id, body.content_type)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.put("/submissions/<int:submission_id>/resubmit")
def resubmit(submission_id: int):
    user = get_current_user()
    db = get_db()
    row = db.get(FanSubmission, submission_id)
    if row is None or row.user_id != user.user_id:
        raise AuthError(404, "not_found", "Submission not found.")
    if row.status not in {"rejected", "pending"}:
        raise AuthError(400, "invalid_status", "Only a pending or returned piece can be edited.")
    body = parse_body(SubmissionIn)
    if not body.rights_confirmed:
        raise AuthError(400, "rights_required", "You must confirm you have the right to share this.")
    from app.account import _edit_wait

    wait = _edit_wait(row)
    if wait:
        raise AuthError(429, "rate_limited", f"You can edit a piece once every 5 minutes. Try again in {wait}.")
    row.category_id = body.category_id
    row.fandom_id = body.fandom_id
    row.content_type = body.content_type
    row.title = body.title.strip()
    row.body = body.body
    row.media_url = body.media_url
    row.source_url = body.source_url
    row.cover_image_url = body.cover_image_url
    row.rights_confirmed = True
    row.status = "pending"
    row.reject_reason = None
    row.reviewed_by = None
    row.reviewed_at = None
    from app.security import utcnow

    row.updated_at = utcnow()
    db.add(ModerationLog(submission_id=row.submission_id, admin_id=user.user_id, action="resubmitted"))
    log_activity(db, user.user_id, "resubmit_content", "submission", row.submission_id)
    db.commit()
    return ok(data=row_dict(row))


@bp.get("/admin/submissions")
def admin_queue():
    get_admin_user()
    db = get_db()
    q = db.query(FanSubmission)
    status = request.args.get("status", "pending")
    if status and status != "all":
        q = q.filter(FanSubmission.status == status)
    rows = q.order_by(FanSubmission.created_at.asc()).all()
    return ok(data=[row_dict(r) for r in rows])


@bp.post("/admin/submissions/<int:submission_id>/review")
def review(submission_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(FanSubmission, submission_id)
    if row is None:
        raise AuthError(404, "not_found", "Submission not found.")
    if row.status != "pending":
        raise AuthError(400, "invalid_status", "That submission is no longer in the queue.")
    body = parse_body(ReviewIn)
    if body.decision not in ("approved", "rejected"):
        raise AuthError(400, "invalid_decision", "decision must be approved or rejected.")
    now = utcnow()
    row.reviewed_by = admin.user_id
    row.reviewed_at = now
    if body.decision == "rejected":
        if not body.reject_reason:
            raise AuthError(400, "reason_required", "A rejection needs a reason.")
        row.status = "rejected"
        row.reject_reason = body.reject_reason
        db.add(ModerationLog(submission_id=row.submission_id, admin_id=admin.user_id, action="rejected", reason=body.reject_reason))
        log_activity(db, admin.user_id, "submission_rejected", "submission", row.submission_id)
        _notify_owner(db, row.user_id, row.title, "rejected", body.reject_reason)
        db.commit()
        return ok(data=row_dict(row), message="Đã rejected.")
    cat_id = body.category_id or row.category_id
    content = Content(
        category_id=cat_id,
        fandom_id=row.fandom_id,
        title=row.title,
        slug=slugify(f"{row.title}-{row.submission_id}"),
        type=row.content_type,
        body=row.body,
        media_url=row.media_url,
        source_url=row.source_url,
        thumbnail_url=row.cover_image_url,
        rights_confirmed=True,
        status="published",
        created_by=row.user_id,
    )
    db.add(content)
    db.flush()
    from app.models import ContentTag

    for tid in body.tag_ids or []:
        if db.get(Tag, tid):
            db.add(ContentTag(content_id=content.content_id, tag_id=tid))
    row.status = "approved"
    row.published_content_id = content.content_id
    db.add(ModerationLog(submission_id=row.submission_id, admin_id=admin.user_id, action="approved"))
    log_activity(db, admin.user_id, "submission_approved", "submission", row.submission_id)
    _notify_owner(db, row.user_id, row.title, "approved and published")
    db.commit()
    return ok(data=row_dict(row, extra={"published_content_id": content.content_id}), message="Đã approved and published.")


@bp.post("/admin/submissions/<int:submission_id>/unpublish")
def unpublish(submission_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(FanSubmission, submission_id)
    if row is None or row.status != "approved" or not row.published_content_id:
        raise AuthError(400, "invalid_status", "Only a published piece can be taken down.")
    from flask import request as flask_request

    payload = flask_request.get_json(silent=True) or {}
    reason = payload.get("reject_reason") or "Taken down after publishing"
    content = db.get(Content, row.published_content_id)
    if content:
        content.status = "archived"
    db.add(ModerationLog(submission_id=row.submission_id, admin_id=admin.user_id, action="rejected", reason=reason))
    log_activity(db, admin.user_id, "submission_unpublish", "submission", row.submission_id)
    _notify_owner(db, row.user_id, row.title, "removed from the site", reason)
    db.commit()
    return ok(data=row_dict(row), message="The published piece was taken down.")
