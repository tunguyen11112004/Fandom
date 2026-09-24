from datetime import date

from flask import Blueprint, request

from app.database import get_db
from app.deps import get_admin_user, get_optional_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Category, MerchandiseImage, MerchandiseItem, MerchandiseTag, Tag
from app.schemas_extra import MerchandiseIn
from app.serialize import arg_int, log_activity, page_args, paginate, row_dict

bp = Blueprint("merchandise", __name__)
bp.strict_slashes = False


def _detail(db, item: MerchandiseItem) -> dict:
    tags = [row_dict(t) for t in db.query(Tag).join(MerchandiseTag, MerchandiseTag.tag_id == Tag.tag_id).filter(MerchandiseTag.item_id == item.item_id).all()]
    images = [row_dict(i) for i in db.query(MerchandiseImage).filter(MerchandiseImage.item_id == item.item_id).order_by(MerchandiseImage.sort_order).all()]
    return row_dict(item, extra={"tags": tags, "images": images, "buyable": False})


def _sync(db, item: MerchandiseItem, tag_ids, images):
    db.query(MerchandiseTag).filter(MerchandiseTag.item_id == item.item_id).delete()
    db.query(MerchandiseImage).filter(MerchandiseImage.item_id == item.item_id).delete()
    for tid in tag_ids or []:
        if db.get(Tag, tid):
            db.add(MerchandiseTag(item_id=item.item_id, tag_id=tid))
    for i, img in enumerate(images or []):
        url = img.get("image_url") if isinstance(img, dict) else None
        if url:
            db.add(MerchandiseImage(item_id=item.item_id, image_url=url, caption=img.get("caption"), sort_order=img.get("sort_order", i)))


@bp.get("/merchandise")
def list_merch():
    db = get_db()
    q = db.query(MerchandiseItem)
    cat = arg_int("category_id")
    if cat:
        q = q.filter(MerchandiseItem.category_id == cat)
    fan = arg_int("fandom_id")
    if fan:
        q = q.filter(MerchandiseItem.fandom_id == fan)
    if request.args.get("upcoming") in ("1", "true", "True"):
        q = q.filter(MerchandiseItem.is_upcoming.is_(True))
    q = q.order_by(MerchandiseItem.created_at.desc())
    page, page_size = page_args()
    items, meta = paginate(q, page, page_size)
    return ok(data={"items": [row_dict(i, extra={"buyable": False}) for i in items], "meta": meta})


@bp.get("/merchandise/upcoming")
def upcoming_merch():
    rows = get_db().query(MerchandiseItem).filter(MerchandiseItem.is_upcoming.is_(True)).order_by(MerchandiseItem.release_date.asc()).all()
    return ok(data=[row_dict(r, extra={"buyable": False}) for r in rows])


@bp.get("/merchandise/<int:item_id>")
def get_merch(item_id: int):
    db = get_db()
    row = db.get(MerchandiseItem, item_id)
    if row is None:
        raise AuthError(404, "not_found", "Không tìm thấy merchandise.")
    row.view_count = (row.view_count or 0) + 1
    user = get_optional_user()
    log_activity(db, user.user_id if user else None, "view", "merchandise", item_id)
    db.commit()
    db.refresh(row)
    return ok(data=_detail(db, row))


@bp.post("/admin/merchandise")
def admin_create_merch():
    admin = get_admin_user()
    db = get_db()
    body = parse_body(MerchandiseIn)
    if db.get(Category, body.category_id) is None:
        raise AuthError(400, "not_found", "Category không tồn tại.")
    data = body.model_dump(exclude={"tag_ids", "images"})
    row = MerchandiseItem(**data)
    db.add(row)
    db.flush()
    _sync(db, row, body.tag_ids, body.images)
    log_activity(db, admin.user_id, "merchandise_create", "merchandise", row.item_id)
    db.commit()
    return ok(data=_detail(db, row), status=201)


@bp.put("/admin/merchandise/<int:item_id>")
def admin_update_merch(item_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(MerchandiseItem, item_id)
    if row is None:
        raise AuthError(404, "not_found", "Không tìm thấy merchandise.")
    body = parse_body(MerchandiseIn)
    for k, v in body.model_dump(exclude={"tag_ids", "images"}).items():
        setattr(row, k, v)
    _sync(db, row, body.tag_ids, body.images)
    log_activity(db, admin.user_id, "merchandise_update", "merchandise", item_id)
    db.commit()
    return ok(data=_detail(db, row))


@bp.delete("/admin/merchandise/<int:item_id>")
def admin_delete_merch(item_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(MerchandiseItem, item_id)
    if row is None:
        raise AuthError(404, "not_found", "Không tìm thấy merchandise.")
    log_activity(db, admin.user_id, "merchandise_delete", "merchandise", item_id)
    db.delete(row)
    db.commit()
    return ok(message="Đã xóa merchandise.")
