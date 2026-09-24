from flask import Blueprint, request

from app.database import get_db
from app.deps import get_admin_user, get_optional_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Category, CharacterProfile, Content, Fandom
from app.schemas_extra import CharacterIn
from app.serialize import arg_int, breadcrumbs, log_activity, page_args, paginate, row_dict

bp = Blueprint("characters", __name__)
bp.strict_slashes = False


@bp.get("/characters")
def list_characters():
    db = get_db()
    q = db.query(CharacterProfile)
    cat = arg_int("category_id")
    if cat:
        q = q.filter(CharacterProfile.category_id == cat)
    fan = arg_int("fandom_id")
    if fan:
        q = q.filter(CharacterProfile.fandom_id == fan)
    qtext = request.args.get("q")
    if qtext:
        like = f"%{qtext}%"
        q = q.filter(CharacterProfile.name.ilike(like))
    q = q.order_by(CharacterProfile.name.asc())
    page, page_size = page_args()
    items, meta = paginate(q, page, page_size)
    return ok(data={"items": [row_dict(i) for i in items], "meta": meta})


@bp.get("/characters/<int:character_id>")
def get_character(character_id: int):
    db = get_db()
    row = db.get(CharacterProfile, character_id)
    if row is None:
        raise AuthError(404, "not_found", "Character not found.")
    row.view_count = (row.view_count or 0) + 1
    user = get_optional_user()
    log_activity(db, user.user_id if user else None, "view", "character", character_id)
    db.commit()
    db.refresh(row)
    related = (
        db.query(Content)
        .filter(Content.status == "published", Content.category_id == row.category_id)
        .order_by(Content.popularity_score.desc())
        .limit(6)
        .all()
    )
    cat = db.get(Category, row.category_id)
    fan = db.get(Fandom, row.fandom_id) if row.fandom_id else None
    return ok(
        data=row_dict(
            row,
            extra={
                "related": [row_dict(c) for c in related],
                "breadcrumbs": breadcrumbs(category=cat, fandom=fan, current=row.name),
            },
        )
    )


@bp.post("/admin/characters")
def admin_create_character():
    admin = get_admin_user()
    db = get_db()
    body = parse_body(CharacterIn)
    if db.get(Category, body.category_id) is None:
        raise AuthError(400, "not_found", "Category not found.")
    row = CharacterProfile(**body.model_dump())
    db.add(row)
    db.flush()
    log_activity(db, admin.user_id, "character_create", "character", row.character_id)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.put("/admin/characters/<int:character_id>")
def admin_update_character(character_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(CharacterProfile, character_id)
    if row is None:
        raise AuthError(404, "not_found", "Character not found.")
    body = parse_body(CharacterIn)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    log_activity(db, admin.user_id, "character_update", "character", character_id)
    db.commit()
    return ok(data=row_dict(row))


@bp.delete("/admin/characters/<int:character_id>")
def admin_delete_character(character_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(CharacterProfile, character_id)
    if row is None:
        raise AuthError(404, "not_found", "Character not found.")
    log_activity(db, admin.user_id, "character_delete", "character", character_id)
    db.delete(row)
    db.commit()
    return ok(message="Character deleted.")
