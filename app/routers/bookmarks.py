import secrets

from flask import Blueprint, request

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Bookmark, CharacterProfile, Content, Event, MerchandiseItem
from app.popularity import refresh_content_popularity
from app.schemas_extra import BookmarkIn, BookmarkNoteIn
from app.serialize import log_activity, row_dict

bp = Blueprint("bookmarks", __name__)
bp.strict_slashes = False


def _target_kind(bm: Bookmark) -> str:
    if bm.content_id:
        return "content"
    if bm.character_id:
        return "character"
    if bm.merchandise_id:
        return "merchandise"
    return "event"


def _exists(db, body: BookmarkIn):
    if body.content_id:
        return db.get(Content, body.content_id) is not None
    if body.character_id:
        return db.get(CharacterProfile, body.character_id) is not None
    if body.merchandise_id:
        return db.get(MerchandiseItem, body.merchandise_id) is not None
    if body.event_id:
        return db.get(Event, body.event_id) is not None
    return False


def _snapshot(db, bm: Bookmark) -> dict:
    available = True
    title = None
    if bm.content_id:
        c = db.get(Content, bm.content_id)
        available = c is not None and c.status == "published"
        title = c.title if c else None
    elif bm.character_id:
        c = db.get(CharacterProfile, bm.character_id)
        available = c is not None
        title = c.name if c else None
    elif bm.merchandise_id:
        c = db.get(MerchandiseItem, bm.merchandise_id)
        available = c is not None
        title = c.name if c else None
    elif bm.event_id:
        c = db.get(Event, bm.event_id)
        available = c is not None
        title = c.title if c else None
    extra = {"target_type": _target_kind(bm), "available": available, "target_title": title}
    if not available:
        extra["unavailable_reason"] = "This item is no longer available."
    return row_dict(bm, extra=extra)


@bp.get("/bookmarks")
def list_bookmarks():
    user = get_current_user()
    db = get_db()
    q = db.query(Bookmark).filter(Bookmark.user_id == user.user_id)
    kind = request.args.get("type")
    if kind == "content":
        q = q.filter(Bookmark.content_id.is_not(None))
    elif kind == "character":
        q = q.filter(Bookmark.character_id.is_not(None))
    elif kind == "merchandise":
        q = q.filter(Bookmark.merchandise_id.is_not(None))
    elif kind == "event":
        q = q.filter(Bookmark.event_id.is_not(None))
    rows = q.order_by(Bookmark.created_at.desc()).all()
    return ok(data=[_snapshot(db, r) for r in rows])


@bp.post("/bookmarks")
def add_bookmark():
    user = get_current_user()
    db = get_db()
    body = parse_body(BookmarkIn)
    ids = [body.content_id, body.character_id, body.merchandise_id, body.event_id]
    if sum(1 for v in ids if v is not None) != 1:
        raise AuthError(400, "invalid_target", "A bookmark must point at exactly one target.")
    if not _exists(db, body):
        raise AuthError(404, "not_found", "That target does not exist.")
    q = db.query(Bookmark).filter(Bookmark.user_id == user.user_id)
    if body.content_id:
        q = q.filter(Bookmark.content_id == body.content_id)
    elif body.character_id:
        q = q.filter(Bookmark.character_id == body.character_id)
    elif body.merchandise_id:
        q = q.filter(Bookmark.merchandise_id == body.merchandise_id)
    else:
        q = q.filter(Bookmark.event_id == body.event_id)
    existing = q.first()
    if existing:
        cid = existing.content_id
        log_activity(db, user.user_id, "bookmark_remove", "bookmark", existing.bookmark_id)
        db.delete(existing)
        refresh_content_popularity(db, cid)
        db.commit()
        return ok(data={"removed": True, "bookmark_id": existing.bookmark_id}, message="Bookmark removed.")
    row = Bookmark(
        user_id=user.user_id,
        content_id=body.content_id,
        character_id=body.character_id,
        merchandise_id=body.merchandise_id,
        event_id=body.event_id,
        note=body.note,
    )
    db.add(row)
    db.flush()
    log_activity(db, user.user_id, "bookmark_add", _target_kind(row), row.bookmark_id)
    refresh_content_popularity(db, row.content_id)
    db.commit()
    return ok(data=_snapshot(db, row), status=201)


@bp.patch("/bookmarks/<int:bookmark_id>")
def update_note(bookmark_id: int):
    user = get_current_user()
    db = get_db()
    row = db.get(Bookmark, bookmark_id)
    if row is None or row.user_id != user.user_id:
        raise AuthError(404, "not_found", "Bookmark not found.")
    body = parse_body(BookmarkNoteIn)
    row.note = body.note
    db.commit()
    return ok(data=row_dict(row))


@bp.delete("/bookmarks/<int:bookmark_id>")
def remove_bookmark(bookmark_id: int):
    user = get_current_user()
    db = get_db()
    row = db.get(Bookmark, bookmark_id)
    if row is None or row.user_id != user.user_id:
        raise AuthError(404, "not_found", "Bookmark not found.")
    log_activity(db, user.user_id, "bookmark_remove", "bookmark", bookmark_id)
    db.delete(row)
    db.commit()
    return ok(message="Bookmark removed.")


@bp.post("/bookmarks/<int:bookmark_id>/share")
def share_bookmark(bookmark_id: int):
    user = get_current_user()
    db = get_db()
    row = db.get(Bookmark, bookmark_id)
    if row is None or row.user_id != user.user_id:
        raise AuthError(404, "not_found", "Bookmark not found.")
    if not row.share_token:
        row.share_token = secrets.token_hex(16)
        db.commit()
    url = f"{settings.public_base_url}{settings.api_prefix}/bookmarks/shared/{row.share_token}"
    return ok(data={"share_token": row.share_token, "url": url, "path": f"/bookmarks/shared/{row.share_token}"})


@bp.get("/bookmarks/shared/<token>")
def shared_bookmark(token: str):
    row = get_db().query(Bookmark).filter(Bookmark.share_token == token).first()
    if row is None:
        raise AuthError(404, "not_found", "That share link is not valid.")
    return ok(data=row_dict(row, extra={"target_type": _target_kind(row)}))
