from flask import Blueprint, request

from app.database import get_db
from app.deps import get_admin_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Category, CharacterProfile, Content, Fandom, Genre, MerchandiseItem, Tag
from app.schemas_extra import CategoryUpdateIn, FandomIn, FandomUpdateIn, TagIn
from app.serialize import arg_int, breadcrumbs, log_activity, row_dict

bp = Blueprint("catalog", __name__)
bp.strict_slashes = False


@bp.get("/categories")
def list_categories():
    rows = get_db().query(Category).order_by(Category.category_id).all()
    return ok(data=[row_dict(r) for r in rows])


@bp.get("/categories/<int:category_id>")
def get_category(category_id: int):
    db = get_db()
    row = db.get(Category, category_id)
    if row is None:
        raise AuthError(404, "not_found", "Category not found.")
    fandoms = db.query(Fandom).filter(Fandom.category_id == category_id, Fandom.is_active.is_(True)).order_by(Fandom.name).all()
    featured = (
        db.query(Content)
        .filter(Content.category_id == category_id, Content.status == "published", Content.is_featured.is_(True))
        .order_by(Content.popularity_score.desc())
        .limit(8)
        .all()
    )
    articles = (
        db.query(Content)
        .filter(Content.category_id == category_id, Content.status == "published", Content.type == "article")
        .order_by(Content.created_at.desc())
        .limit(8)
        .all()
    )
    media = (
        db.query(Content)
        .filter(Content.category_id == category_id, Content.status == "published", Content.type.in_(["video", "audio", "trailer", "explainer", "image"]))
        .order_by(Content.created_at.desc())
        .limit(8)
        .all()
    )
    chars = db.query(CharacterProfile).filter(CharacterProfile.category_id == category_id).order_by(CharacterProfile.name).limit(8).all()
    merch = db.query(MerchandiseItem).filter(MerchandiseItem.category_id == category_id).order_by(MerchandiseItem.created_at.desc()).limit(8).all()
    return ok(
        data={
            **row_dict(row),
            "breadcrumbs": breadcrumbs(category=row),
            "fandoms": [row_dict(f) for f in fandoms],
            "featured": [row_dict(c) for c in featured],
            "articles": [row_dict(c) for c in articles],
            "media": [row_dict(c) for c in media],
            "characters": [row_dict(c) for c in chars],
            "merchandise": [row_dict(m, extra={"buyable": False}) for m in merch],
        }
    )


@bp.get("/categories/<int:category_id>/fandoms")
def list_category_fandoms(category_id: int):
    db = get_db()
    if db.get(Category, category_id) is None:
        raise AuthError(404, "not_found", "Category not found.")
    q = db.query(Fandom).filter(Fandom.category_id == category_id, Fandom.is_active.is_(True))
    return ok(data=[row_dict(r) for r in q.order_by(Fandom.name).all()])


@bp.get("/fandoms")
def list_fandoms():
    db = get_db()
    q = db.query(Fandom).filter(Fandom.is_active.is_(True))
    cat = arg_int("category_id")
    if cat:
        q = q.filter(Fandom.category_id == cat)
    return ok(data=[row_dict(r) for r in q.order_by(Fandom.name).all()])


@bp.get("/fandoms/<int:fandom_id>")
def get_fandom(fandom_id: int):
    row = get_db().get(Fandom, fandom_id)
    if row is None or not row.is_active:
        raise AuthError(404, "not_found", "Fandom not found.")
    return ok(data=row_dict(row))


@bp.get("/genres")
def list_genres():
    return ok(data=[row_dict(r) for r in get_db().query(Genre).order_by(Genre.name).all()])


@bp.get("/tags")
def list_tags():
    return ok(data=[row_dict(r) for r in get_db().query(Tag).order_by(Tag.name).all()])


@bp.put("/admin/categories/<int:category_id>")
def admin_update_category(category_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Category, category_id)
    if row is None:
        raise AuthError(404, "not_found", "Category not found.")
    body = parse_body(CategoryUpdateIn)
    row.name = body.name.strip()
    row.slug = body.slug.strip()
    row.description = body.description
    row.cover_url = body.cover_url
    log_activity(db, admin.user_id, "category_update", "category", category_id)
    db.commit()
    return ok(data=row_dict(row))


@bp.post("/admin/fandoms")
def admin_create_fandom():
    admin = get_admin_user()
    db = get_db()
    body = parse_body(FandomIn)
    if db.get(Category, body.category_id) is None:
        raise AuthError(400, "not_found", "Category not found.")
    row = Fandom(
        category_id=body.category_id,
        name=body.name.strip(),
        slug=body.slug.strip(),
        description=body.description,
        cover_url=body.cover_url,
        is_active=True if body.is_active is None else body.is_active,
    )
    db.add(row)
    db.flush()
    log_activity(db, admin.user_id, "fandom_create", "fandom", row.fandom_id)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.put("/admin/fandoms/<int:fandom_id>")
def admin_update_fandom(fandom_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Fandom, fandom_id)
    if row is None:
        raise AuthError(404, "not_found", "Fandom not found.")
    body = parse_body(FandomUpdateIn)
    if body.category_id is not None:
        if db.get(Category, body.category_id) is None:
            raise AuthError(400, "not_found", "Category not found.")
        row.category_id = body.category_id
    if body.name is not None:
        row.name = body.name.strip()
    if body.slug is not None:
        row.slug = body.slug.strip()
    if body.description is not None:
        row.description = body.description
    if body.cover_url is not None:
        row.cover_url = body.cover_url
    if body.is_active is not None:
        row.is_active = body.is_active
    log_activity(db, admin.user_id, "fandom_update", "fandom", fandom_id)
    db.commit()
    return ok(data=row_dict(row))


@bp.delete("/admin/fandoms/<int:fandom_id>")
def admin_delete_fandom(fandom_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Fandom, fandom_id)
    if row is None:
        raise AuthError(404, "not_found", "Fandom not found.")
    from app.models import CharacterProfile, Content, Event, MerchandiseItem, UserFandom

    refs = (
        db.query(Content).filter(Content.fandom_id == fandom_id).count()
        + db.query(CharacterProfile).filter(CharacterProfile.fandom_id == fandom_id).count()
        + db.query(MerchandiseItem).filter(MerchandiseItem.fandom_id == fandom_id).count()
        + db.query(Event).filter(Event.fandom_id == fandom_id).count()
        + db.query(UserFandom).filter(UserFandom.fandom_id == fandom_id).count()
    )
    if refs:
        raise AuthError(409, "in_use", "That fandom is in use. Hide it (is_active=false) instead of deleting it.")
    log_activity(db, admin.user_id, "fandom_delete", "fandom", fandom_id)
    db.delete(row)
    db.commit()
    return ok(message="Fandom deleted.")


@bp.post("/admin/tags")
def admin_create_tag():
    admin = get_admin_user()
    db = get_db()
    body = parse_body(TagIn)
    row = Tag(name=body.name.strip())
    db.add(row)
    db.flush()
    log_activity(db, admin.user_id, "tag_create", "tag", row.tag_id)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.put("/admin/tags/<int:tag_id>")
def admin_update_tag(tag_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Tag, tag_id)
    if row is None:
        raise AuthError(404, "not_found", "Tag not found.")
    body = parse_body(TagIn)
    row.name = body.name.strip()
    log_activity(db, admin.user_id, "tag_update", "tag", tag_id)
    db.commit()
    return ok(data=row_dict(row))


@bp.delete("/admin/tags/<int:tag_id>")
def admin_delete_tag(tag_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Tag, tag_id)
    if row is None:
        raise AuthError(404, "not_found", "Tag not found.")
    log_activity(db, admin.user_id, "tag_delete", "tag", tag_id)
    db.delete(row)
    db.commit()
    return ok(message="Tag deleted.")
