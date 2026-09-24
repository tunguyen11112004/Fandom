from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from flask import Blueprint, request

from app.database import get_db
from app.deps import get_admin_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Event
from app.schemas_extra import EventIn
from app.serialize import arg_int, log_activity, page_args, paginate, row_dict

bp = Blueprint("events", __name__)
bp.strict_slashes = False


def _haversine(lat1, lon1, lat2, lon2):
    r = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


@bp.get("/events")
def list_events():
    db = get_db()
    q = db.query(Event)
    city = request.args.get("city")
    if city:
        q = q.filter(Event.city.ilike(city))
    etype = request.args.get("event_type")
    if etype:
        q = q.filter(Event.event_type == etype)
    cat = arg_int("category_id")
    if cat:
        q = q.filter(Event.category_id == cat)
    start = request.args.get("start")
    end = request.args.get("end")
    if start:
        q = q.filter(Event.start_at >= datetime.fromisoformat(start))
    if end:
        q = q.filter(Event.start_at <= datetime.fromisoformat(end))
    q = q.order_by(Event.start_at.asc())
    page, page_size = page_args()
    items, meta = paginate(q, page, page_size)
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    radius = request.args.get("radius_km")
    out = []
    for ev in items:
        data = row_dict(ev)
        if lat and lng and ev.latitude is not None and ev.longitude is not None:
            dist = _haversine(float(lat), float(lng), ev.latitude, ev.longitude)
            data["distance_km"] = round(dist, 2)
            if radius and dist > float(radius):
                continue
        out.append(data)
    return ok(data={"items": out, "meta": meta})


@bp.get("/events/<int:event_id>")
def get_event(event_id: int):
    row = get_db().get(Event, event_id)
    if row is None:
        raise AuthError(404, "not_found", "Event not found.")
    return ok(data=row_dict(row))


@bp.post("/admin/events")
def admin_create_event():
    admin = get_admin_user()
    db = get_db()
    body = parse_body(EventIn)
    if body.latitude is not None and not (-90 <= body.latitude <= 90):
        raise AuthError(400, "invalid_geo", "latitude is not valid.")
    if body.longitude is not None and not (-180 <= body.longitude <= 180):
        raise AuthError(400, "invalid_geo", "longitude is not valid.")
    row = Event(**body.model_dump(), created_by=admin.user_id)
    db.add(row)
    db.flush()
    log_activity(db, admin.user_id, "event_create", "event", row.event_id)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.put("/admin/events/<int:event_id>")
def admin_update_event(event_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Event, event_id)
    if row is None:
        raise AuthError(404, "not_found", "Event not found.")
    body = parse_body(EventIn)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    log_activity(db, admin.user_id, "event_update", "event", event_id)
    db.commit()
    return ok(data=row_dict(row))


@bp.delete("/admin/events/<int:event_id>")
def admin_delete_event(event_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(Event, event_id)
    if row is None:
        raise AuthError(404, "not_found", "Event not found.")
    log_activity(db, admin.user_id, "event_delete", "event", event_id)
    db.delete(row)
    db.commit()
    return ok(message="Event deleted.")
