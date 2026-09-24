from datetime import date, datetime
from math import ceil

from flask import request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.errors import AuthError
from app.models import ActivityLog, ContentRating


def row_dict(obj, extra: dict | None = None, exclude: set[str] | None = None) -> dict:
    skip = exclude or set()
    data = {}
    for col in obj.__table__.columns:
        if col.name in skip:
            continue
        val = getattr(obj, col.name)
        if isinstance(val, (datetime, date)):
            val = val.isoformat()
        data[col.name] = val
    if extra:
        data.update(extra)
    return data


def page_args():
    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(100, max(1, int(request.args.get("page_size", 20))))
    except ValueError:
        raise AuthError(400, "invalid_page", "page/page_size không hợp lệ.")
    return page, page_size


def paginate(query, page: int, page_size: int):
    total = query.order_by(None).count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": ceil(total / page_size) if page_size else 0,
    }


def log_activity(db: Session, user_id: int | None, action: str, entity_type: str | None = None, entity_id: int | None = None, details: str | None = None) -> None:
    db.add(ActivityLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details))


def rating_summary(db: Session, content_id: int) -> dict:
    row = (
        db.query(func.avg(ContentRating.score), func.count(ContentRating.rating_id))
        .filter(ContentRating.content_id == content_id)
        .one()
    )
    avg, count = row
    return {"avg_score": round(float(avg), 2) if avg is not None else None, "rating_count": int(count or 0)}


def slugify(text: str) -> str:
    raw = "".join(ch.lower() if ch.isalnum() else "-" for ch in (text or "").strip())
    while "--" in raw:
        raw = raw.replace("--", "-")
    return raw.strip("-") or "item"


def arg_int(name: str, default=None):
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError:
        raise AuthError(400, "invalid_query", f"{name} phải là số.")


def breadcrumbs(category=None, fandom=None, current: str | None = None) -> list[dict]:
    crumbs = [{"label": "Home", "path": "/"}]
    if category is not None:
        crumbs.append({"label": category.name, "path": f"/categories/{category.category_id}"})
    if fandom is not None:
        crumbs.append({"label": fandom.name, "path": f"/fandoms/{fandom.fandom_id}"})
    if current:
        crumbs.append({"label": current, "path": None})
    return crumbs

