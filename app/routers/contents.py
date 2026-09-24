from datetime import date

from flask import Blueprint, request
from sqlalchemy import or_

from app.database import get_db
from app.deps import get_admin_user, get_current_user, get_optional_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import (
    Category,
    Content,
    ContentGenre,
    ContentImage,
    ContentRating,
    ContentTag,
    ContentTimelineEntry,
    Fandom,
    Genre,
    Tag,
)
from app.popularity import refresh_content_popularity
from app.schemas_extra import ContentIn, RatingIn
from app.serialize import arg_int, breadcrumbs, log_activity, page_args, paginate, rating_summary, row_dict, slugify

bp = Blueprint("contents", __name__)

bp = Blueprint("contents", __name__)
bp.strict_slashes = False
MEDIA_TYPES = {"video", "audio", "trailer", "explainer"}
SORTS = {"latest", "popular", "alpha"}
EMBED_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "spotify.com")


def _check_embed(url: str | None) -> None:
    if not url:
        return
    from urllib.parse import urlparse

    host = (urlparse(url).netloc or "").lower()
    if not any(h in host for h in EMBED_HOSTS):
        raise AuthError(400, "invalid_embed", "Chỉ cho phép nhúng YouTube, Vimeo hoặc Spotify.")



def _public_q(db):
    return db.query(Content).filter(Content.status == "published")


def _sync_relations(db, content: Content, genre_ids, tag_ids, images, timeline):
    db.query(ContentGenre).filter(ContentGenre.content_id == content.content_id).delete()
    db.query(ContentTag).filter(ContentTag.content_id == content.content_id).delete()
    db.query(ContentImage).filter(ContentImage.content_id == content.content_id).delete()
    db.query(ContentTimelineEntry).filter(ContentTimelineEntry.content_id == content.content_id).delete()
    for gid in genre_ids or []:
        if db.get(Genre, gid):
            db.add(ContentGenre(content_id=content.content_id, genre_id=gid))
    for tid in tag_ids or []:
        if db.get(Tag, tid):
            db.add(ContentTag(content_id=content.content_id, tag_id=tid))
    for i, img in enumerate(images or []):
        url = img.get("image_url") if isinstance(img, dict) else None
        if url:
            db.add(ContentImage(content_id=content.content_id, image_url=url, caption=img.get("caption"), sort_order=img.get("sort_order", i)))
    for i, ent in enumerate(timeline or []):
        if isinstance(ent, dict) and ent.get("title"):
            db.add(
                ContentTimelineEntry(
                    content_id=content.content_id,
                    title=ent["title"],
                    description=ent.get("description"),
                    image_url=ent.get("image_url"),
                    entry_date=ent.get("entry_date"),
                    sort_order=ent.get("sort_order", i),
                )
            )


def _detail(db, content: Content) -> dict:
    genres = [row_dict(g) for g in db.query(Genre).join(ContentGenre).filter(ContentGenre.content_id == content.content_id).all()]
    tags = [row_dict(t) for t in db.query(Tag).join(ContentTag).filter(ContentTag.content_id == content.content_id).all()]
    images = [row_dict(i) for i in db.query(ContentImage).filter(ContentImage.content_id == content.content_id).order_by(ContentImage.sort_order).all()]
    timeline = [row_dict(t) for t in db.query(ContentTimelineEntry).filter(ContentTimelineEntry.content_id == content.content_id).order_by(ContentTimelineEntry.sort_order).all()]
    related = (
        _public_q(db)
        .filter(Content.category_id == content.category_id, Content.content_id != content.content_id)
        .order_by(Content.popularity_score.desc())
        .limit(6)
        .all()
    )
    if content.fandom_id:
        related_fan = (
            _public_q(db)
            .filter(Content.fandom_id == content.fandom_id, Content.content_id != content.content_id)
            .order_by(Content.popularity_score.desc())
            .limit(4)
            .all()
        )
        seen = {r.content_id for r in related}
        related = related + [r for r in related_fan if r.content_id not in seen]
    cat = db.get(Category, content.category_id)
    fan = db.get(Fandom, content.fandom_id) if content.fandom_id else None
    return row_dict(
        content,
        extra={
            "genres": genres,
            "tags": tags,
            "images": images,
            "timeline": timeline,
            "rating": rating_summary(db, content.content_id),
            "related": [row_dict(r) for r in related[:6]],
            "breadcrumbs": breadcrumbs(category=cat, fandom=fan, current=content.title),
        },
    )


@bp.get("/contents")
def list_contents():
    db = get_db()
    user = get_optional_user()
    qtext = request.args.get("q")
    cat = arg_int("category_id")
    fan = arg_int("fandom_id")
    genre_id = arg_int("genre_id")
    ctype = request.args.get("type")
    year = arg_int("year")
    featured = request.args.get("featured")
    sort = request.args.get("sort", "latest")
    advanced = any([genre_id, year, fan, featured in ("1", "true", "True"), sort not in ("latest", "", None)])
    if advanced and user is None:
        raise AuthError(401, "login_required", "Lọc/sắp xếp nâng cao dành cho thành viên. Hãy đăng nhập.")
    q = _public_q(db)
    if qtext:
        like = f"%{qtext}%"
        q = q.filter(or_(Content.title.ilike(like), Content.description.ilike(like), Content.summary.ilike(like)))
    if cat:
        q = q.filter(Content.category_id == cat)
    if fan:
        q = q.filter(Content.fandom_id == fan)
    if genre_id:
        q = q.join(ContentGenre, ContentGenre.content_id == Content.content_id).filter(ContentGenre.genre_id == genre_id).distinct()
    if ctype:
        q = q.filter(Content.type == ctype)
    if year:
        q = q.filter(Content.release_date.is_not(None)).filter(Content.release_date >= date(year, 1, 1)).filter(Content.release_date <= date(year, 12, 31))
    if featured in ("1", "true", "True"):
        q = q.filter(Content.is_featured.is_(True))
    if sort not in SORTS:
        raise AuthError(400, "invalid_sort", "sort phải là latest, popular hoặc alpha.")
    if sort == "popular":
        q = q.order_by(Content.popularity_score.desc(), Content.view_count.desc())
    elif sort == "alpha":
        q = q.order_by(Content.title.asc())
    else:
        q = q.order_by(Content.created_at.desc())
    page, page_size = page_args()
    items, meta = paginate(q, page, page_size)
    applied = {k: v for k, v in {
        "q": qtext, "category_id": cat, "fandom_id": fan, "genre_id": genre_id, "type": ctype, "year": year, "sort": sort
    }.items() if v not in (None, "")}
    empty_hint = None
    if not items:
        empty_hint = "Không có kết quả. Hãy nới bộ lọc hoặc hỏi chatbot."
    return ok(data={"items": [row_dict(i) for i in items], "meta": meta, "applied_filters": applied, "empty_hint": empty_hint})


@bp.get("/contents/featured")
def featured():
    rows = _public_q(get_db()).filter(Content.is_featured.is_(True)).order_by(Content.popularity_score.desc()).limit(20).all()
    return ok(data=[row_dict(r) for r in rows])


@bp.get("/contents/upcoming")
def upcoming():
    rows = (
        _public_q(get_db())
        .filter(Content.release_date.is_not(None), Content.release_date > date.today())
        .order_by(Content.release_date.asc())
        .all()
    )
    return ok(data=[row_dict(r) for r in rows])


@bp.get("/releases/upcoming")
def upcoming_all():
    db = get_db()
    contents = (
        _public_q(db)
        .filter(Content.release_date.is_not(None), Content.release_date > date.today())
        .order_by(Content.release_date.asc())
        .all()
    )
    from app.models import MerchandiseItem

    merch = db.query(MerchandiseItem).filter(MerchandiseItem.is_upcoming.is_(True)).order_by(MerchandiseItem.release_date.asc()).all()
    items = (
        [row_dict(c, extra={"source": "content", "name": c.title}) for c in contents]
        + [row_dict(m, extra={"source": "merchandise", "buyable": False}) for m in merch]
    )
    items.sort(key=lambda x: x.get("release_date") or "")
    return ok(data=items)


@bp.get("/contents/<int:content_id>")
def get_content(content_id: int):
    db = get_db()
    row = db.get(Content, content_id)
    if row is None or row.status != "published":
        raise AuthError(404, "not_found", "Không tìm thấy nội dung.")
    row.view_count = (row.view_count or 0) + 1
    user = get_optional_user()
    log_activity(db, user.user_id if user else None, "view", "content", content_id)
    refresh_content_popularity(db, content_id)
    db.commit()
    db.refresh(row)
    return ok(data=_detail(db, row))


@bp.post("/contents/<int:content_id>/ratings")
def rate_content(content_id: int):
    user = get_current_user()
    db = get_db()
    content = db.get(Content, content_id)
    if content is None or content.status != "published":
        raise AuthError(404, "not_found", "Không tìm thấy nội dung.")
    body = parse_body(RatingIn)
    row = db.query(ContentRating).filter(ContentRating.user_id == user.user_id, ContentRating.content_id == content_id).first()
    if row:
        row.score = body.score
    else:
        db.add(ContentRating(user_id=user.user_id, content_id=content_id, score=body.score))
    log_activity(db, user.user_id, "rate", "content", content_id, f"score={body.score}")
    refresh_content_popularity(db, content_id)
    db.commit()
    return ok(data=rating_summary(db, content_id), message="Đã lưu đánh giá.")


@bp.post("/admin/contents")
def admin_create_content():
    admin = get_admin_user()
    db = get_db()
    body = parse_body(ContentIn)
    if db.get(Category, body.category_id) is None:
        raise AuthError(400, "not_found", "Category không tồn tại.")
    if body.status == "published" and body.type in MEDIA_TYPES and (not body.source_url or not body.rights_confirmed):
        raise AuthError(400, "rights_required", "Media published cần source_url và rights_confirmed.")
    _check_embed(body.embed_url)
    row = Content(
        category_id=body.category_id,
        fandom_id=body.fandom_id,
        title=body.title.strip(),
        slug=(body.slug or slugify(body.title)).strip(),
        type=body.type,
        summary=body.summary,
        description=body.description,
        body=body.body,
        media_url=body.media_url,
        embed_url=body.embed_url,
        source_name=body.source_name,
        source_url=body.source_url,
        license_url=body.license_url,
        rights_confirmed=body.rights_confirmed,
        thumbnail_url=body.thumbnail_url,
        duration_seconds=body.duration_seconds,
        release_date=body.release_date,
        is_featured=body.is_featured,
        status=body.status,
        created_by=admin.user_id,
    )
    db.add(row)
    db.flush()
    _sync_relations(db, row, body.genre_ids, body.tag_ids, body.images, body.timeline)
    log_activity(db, admin.user_id, "content_create", "content", row.content_id)
    db.commit()
    return ok(data=_detail(db, row), status=201)


@bp.put("/admin/contents/<int:content_id>")
def admin_update_content(content_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Content, content_id)
    if row is None:
        raise AuthError(404, "not_found", "Không tìm thấy nội dung.")
    body = parse_body(ContentIn)
    if body.status == "published" and body.type in MEDIA_TYPES and (not body.source_url or not body.rights_confirmed):
        raise AuthError(400, "rights_required", "Media published cần source_url và rights_confirmed.")
    _check_embed(body.embed_url)
    for field in (
        "category_id", "fandom_id", "title", "type", "summary", "description", "body", "media_url",
        "embed_url", "source_name", "source_url", "license_url", "rights_confirmed", "thumbnail_url",
        "duration_seconds", "release_date", "is_featured", "status",
    ):
        setattr(row, field, getattr(body, field) if field != "title" else body.title.strip())
    row.slug = (body.slug or row.slug or slugify(body.title)).strip()
    _sync_relations(db, row, body.genre_ids, body.tag_ids, body.images, body.timeline)
    log_activity(db, admin.user_id, "content_update", "content", content_id)
    db.commit()
    return ok(data=_detail(db, row))


@bp.delete("/admin/contents/<int:content_id>")
def admin_delete_content(content_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Content, content_id)
    if row is None:
        raise AuthError(404, "not_found", "Không tìm thấy nội dung.")
    row.status = "archived"
    log_activity(db, admin.user_id, "content_unpublish", "content", content_id, "archived")
    db.commit()
    return ok(data=row_dict(row), message="Đã ẩn nội dung (archived). Bookmark sẽ hiện không còn khả dụng.")


@bp.get("/admin/contents")
def admin_list_contents():
    get_admin_user()
    db = get_db()
    q = db.query(Content)
    status = request.args.get("status")
    if status:
        q = q.filter(Content.status == status)
    rows = q.order_by(Content.updated_at.desc()).limit(200).all()
    return ok(data=[row_dict(r) for r in rows])
