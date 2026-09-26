import json
import uuid
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, abort, current_app, jsonify, redirect, render_template, request, session, stream_with_context, url_for
from sqlalchemy import and_, func, or_

from .account import current_user
from .paging import page_of
from .security import like_contains
from .events import haversine_km
from .extensions import db
from .models import (
    ActivityLog,
    Bookmark,
    Category,
    CharacterProfile,
    ChatSession,
    ChatbotQuery,
    Content,
    ContentGenre,
    ContentRating,
    Event,
    Fandom,
    Genre,
    MerchandiseItem,
    MerchandiseTag,
    Tag,
)
from .news import featured_worlds, news_items
from .popularity import refresh_content_popularity
from .serialize import rating_summary
from .series import hottest
from .ai.service import fandom_chat
from .support import related_links, reply_to

bp = Blueprint("main", __name__)

POPULARITY_BANDS = {
    "iconic": (90, 100),
    "notable": (75, 89),
    "rising": (0, 74),
}

SORTS = {
    "latest": "Latest releases",
    "popular": "Most popular",
    "alpha": "Alphabetical",
}


def _apply_filters(query, args):
    q = args.get("q", "").strip()
    category = args.get("category", "").strip()
    genre = args.get("genre", "").strip()
    year = args.get("year", "").strip()
    content_type = args.get("type", "").strip()
    popularity = args.get("popularity", "").strip()
    fandom = args.get("fandom", "").strip()
    featured = args.get("featured", "").strip()

    query = query.filter(Content.status == "published")
    if q:
        like = like_contains(q)
        query = query.filter(
            or_(
                Content.title.ilike(like),
                Content.summary.ilike(like),
            )
        )
    if category:
        query = query.filter(Category.slug == category)
    if genre:
        query = query.join(ContentGenre, ContentGenre.content_id == Content.content_id).join(
            Genre, Genre.genre_id == ContentGenre.genre_id
        ).filter(Genre.name == genre)
    if year.isdigit():
        query = query.filter(func.year(Content.release_date) == int(year))
    if content_type:
        query = query.filter(Content.type == content_type)
    if popularity in POPULARITY_BANDS:
        low, high = POPULARITY_BANDS[popularity]
        query = query.filter(Content.popularity_score.between(low, high))
    if fandom:
        query = query.join(Fandom, Fandom.fandom_id == Content.fandom_id).filter(Fandom.slug == fandom, Fandom.is_active.is_(True))
    if featured == "yes":
        query = query.filter(Content.is_featured.is_(True))

    return query


def _explore_chips(filters, sort):
    labels = {
        "q": filters["q"],
        "category": filters["category"],
        "genre": filters["genre"],
        "year": filters["year"],
        "type": filters["type"],
        "popularity": filters["popularity"],
        "fandom": filters["fandom"],
        "featured": "Featured" if filters["featured"] == "yes" else "",
        "sort": SORTS.get(sort, "") if sort != "latest" else "",
    }
    chips = []
    for key, label in labels.items():
        if not label:
            continue
        kept = {name: value for name, value in filters.items() if value and name != key}
        if key != "sort" and sort != "latest":
            kept["sort"] = sort
        chips.append({"label": label, "href": url_for("main.explore", **kept)})
    return chips


def _apply_sort(query, sort):
    if sort == "popular":
        return query.order_by(Content.popularity_score.desc(), Content.title.asc())
    if sort == "alpha":
        return query.order_by(func.lower(Content.title).asc())
    return query.order_by(Content.release_date.desc(), Content.title.asc())


@bp.route("/")
def home():
    categories = Category.query.order_by(Category.category_id).all()
    counts = dict(
        db_counts()
    )
    return render_template(
        "home.html",
        categories=categories,
        counts=counts,
        total=Content.query.filter_by(status="published").count(),
        headlines=news_items(limit=4),
        hottest=hottest(limit=None),
    )


def db_counts():
    rows = (
        Category.query.outerjoin(
            Content,
            and_(Content.category_id == Category.category_id, Content.status == "published"),
        )
        .with_entities(Category.slug, func.count(Content.content_id))
        .group_by(Category.category_id)
        .all()
    )
    return rows


def _guest_advanced(args, viewer):
    if viewer is not None and (viewer.is_member or viewer.role == "admin"):
        return False
    sort = args.get("sort", "latest")
    return any(
        [
            args.get("genre", "").strip(),
            args.get("year", "").strip(),
            args.get("popularity", "").strip(),
            args.get("fandom", "").strip(),
            args.get("featured", "").strip() == "yes",
            sort not in ("", "latest"),
        ]
    )


@bp.route("/explore")
def explore():
    viewer = current_user()
    if _guest_advanced(request.args, viewer):
        return redirect(url_for("account.login", next=request.full_path))

    sort = request.args.get("sort", "latest")
    if sort not in SORTS:
        sort = "latest"

    query = _apply_sort(
        _apply_filters(Content.query.join(Category), request.args),
        sort,
    )
    page = request.args.get("page", "1")
    page = int(page) if page.isdigit() and int(page) > 0 else 1
    per_page = 12
    total_items = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, (total_items + per_page - 1) // per_page)
    categories = Category.query.order_by(Category.name).all()
    genres = [
        row[0]
        for row in db.session.query(Genre.name)
        .join(ContentGenre, ContentGenre.genre_id == Genre.genre_id)
        .distinct()
        .order_by(Genre.name)
        .all()
    ]
    years = [
        row[0]
        for row in Content.query.with_entities(func.year(Content.release_date))
        .filter(Content.release_date.isnot(None))
        .distinct()
        .order_by(func.year(Content.release_date).desc())
        .all()
    ]
    active_category = request.args.get("category", "").strip()
    category_name = None
    if active_category:
        match = Category.query.filter_by(slug=active_category).first()
        category_name = match.name if match else None
    fandoms = Fandom.query.filter_by(is_active=True).order_by(Fandom.name).all()
    filters = {
        "q": request.args.get("q", "").strip(),
        "category": active_category,
        "genre": request.args.get("genre", "").strip(),
        "year": request.args.get("year", "").strip(),
        "type": request.args.get("type", "").strip(),
        "popularity": request.args.get("popularity", "").strip(),
        "fandom": request.args.get("fandom", "").strip(),
        "featured": request.args.get("featured", "").strip(),
    }

    return render_template(
        "explore.html",
        items=items,
        categories=categories,
        genres=genres,
        years=years,
        fandoms=fandoms,
        content_types=("article", "video", "audio", "image", "trailer", "explainer"),
        sorts=SORTS,
        sort=sort,
        filters=filters,
        chips=_explore_chips(filters, sort),
        category_name=category_name,
        shelf=hottest(limit=None) if active_category in {"anime", "manga"} else [],
        can_filter=viewer is not None and (viewer.is_member or viewer.role == "admin"),
        page=page,
        pages=pages,
        total_items=total_items,
    )


@bp.route("/explore/<slug>")
def content_detail(slug):
    item = Content.query.filter_by(slug=slug).first()
    viewer = current_user()
    if item is None or (item.status != "published" and (viewer is None or viewer.role != "admin")):
        abort(404)
    item.view_count = (item.view_count or 0) + 1
    refresh_content_popularity(db.session, item.content_id)
    saved = None
    my_score = None
    if viewer is not None and viewer.is_member:
        saved = Bookmark.query.filter_by(user_id=viewer.user_id, content_id=item.content_id).first()
        rated = ContentRating.query.filter_by(user_id=viewer.user_id, content_id=item.content_id).first()
        my_score = rated.score if rated else None
        db.session.add(
            ActivityLog(
                user_id=viewer.user_id,
                action="view",
                entity_type="content",
                entity_id=item.content_id,
                details=f"Opened {item.title}"[:255],
            )
        )
    db.session.commit()
    related = (
        Content.query.filter(
            Content.category_id == item.category_id,
            Content.content_id != item.content_id,
            Content.status == "published",
        )
        .order_by(Content.popularity_score.desc())
        .limit(3)
        .all()
    )
    player, media_src = _media_player(item)
    timeline = sorted(item.timeline, key=lambda row: (row.sort_order, row.entry_date or date.min))
    return render_template(
        "detail.html",
        item=item,
        related=related,
        saved=saved,
        rating=rating_summary(db.session, item.content_id),
        my_score=my_score,
        player=player,
        media_src=media_src,
        timeline=timeline,
    )


@bp.route("/media")
@bp.route("/media/<slug>")
def media_center(slug=None):
    kinds = ("video", "trailer", "explainer", "audio", "image")
    labels = {
        "video": "Video",
        "trailer": "Trailers",
        "explainer": "Explainers",
        "audio": "Audio",
        "image": "Image sets",
    }
    rows = (
        Content.query.filter(Content.status == "published", Content.type.in_(kinds))
        .order_by(Content.release_date.desc(), Content.title.asc())
        .all()
    )
    shelf_rows, page, pages, _ = page_of(rows, 12)
    groups = []
    for kind in kinds:
        shelf = [row for row in shelf_rows if row.type == kind]
        if shelf:
            groups.append({"kind": kind, "label": labels[kind], "items": shelf})
    now = None
    if slug:
        now = next((row for row in rows if row.slug == slug), None)
        if now is None:
            abort(404)
        now.view_count = (now.view_count or 0) + 1
        refresh_content_popularity(db.session, now.content_id)
        viewer = current_user()
        if viewer is not None and viewer.is_member:
            db.session.add(
                ActivityLog(
                    user_id=viewer.user_id,
                    action="view",
                    entity_type="content",
                    entity_id=now.content_id,
                    details=f"Played {now.title}"[:255],
                )
            )
        db.session.commit()
    elif groups:
        now = groups[0]["items"][0]
    player, media_src = _media_player(now) if now is not None else (None, None)
    my_score = None
    viewer = current_user()
    if now is not None and viewer is not None and viewer.is_member:
        rated = ContentRating.query.filter_by(user_id=viewer.user_id, content_id=now.content_id).first()
        my_score = rated.score if rated else None
    return render_template(
        "media.html",
        groups=groups,
        now=now,
        player=player,
        media_src=media_src,
        my_score=my_score,
        rating=rating_summary(db.session, now.content_id) if now is not None else None,
        page=page,
        pages=pages,
    )


def _embed_src(url):
    if not url:
        return None
    if "watch?v=" in url:
        return url.replace("watch?v=", "embed/")
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if "youtube.com/shorts/" in url:
        video_id = url.split("shorts/")[-1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}"
    return url


def _media_player(item):
    url = (item.embed_url or item.media_url or "").strip()
    if not url or url.lower() == "none":
        return None, None
    lower = url.lower().split("?")[0]
    if "youtu.be/" in url or "youtube.com" in url or "youtube-nocookie.com" in url:
        return "youtube", _embed_src(url)
    if lower.endswith((".mp3", ".wav", ".m4a", ".ogg")) or item.type == "audio":
        return "audio", url
    if lower.endswith((".mp4", ".webm")) or item.type in {"video", "trailer", "explainer"}:
        return "video", url
    return "link", url


@bp.route("/news")
def news_legacy():
    return redirect(url_for("main.news", **request.args.to_dict(flat=True)))


@bp.route("/featured")
def news():
    worlds = featured_worlds()
    world = request.args.get("world", "").strip()
    if world not in {w["slug"] for w in worlds}:
        world = ""
    items = news_items(world or None)
    news_total = len(items)
    items, page, pages, _ = page_of(items, 6)
    return render_template(
        "news.html",
        items=items,
        news_total=news_total,
        page=page,
        pages=pages,
        world=world,
        worlds=worlds,
    )


def _chat_session():
    token = session.get("sid")
    if not token:
        token = uuid.uuid4().hex
        session["sid"] = token
    row = ChatSession.query.filter_by(session_token=token).first()
    if row is None:
        row = ChatSession(session_token=token)
        db.session.add(row)
        db.session.commit()
    viewer = current_user()
    if viewer is not None and row.user_id is None:
        row.user_id = viewer.user_id
        db.session.commit()
    return row


def _save_turn(role, message, faq_id=None):
    chat = _chat_session()
    if role == "user":
        db.session.add(ChatbotQuery(session_id=chat.session_id, message=message, response=None))
    else:
        last = (
            ChatbotQuery.query.filter_by(session_id=chat.session_id)
            .order_by(ChatbotQuery.query_id.desc())
            .first()
        )
        if last is not None and last.response is None:
            last.response = message
            last.matched_faq_id = faq_id
        else:
            db.session.add(ChatbotQuery(session_id=chat.session_id, message="", response=message, matched_faq_id=faq_id))
    db.session.commit()


@bp.route("/support/history")
def support_history():
    chat = _chat_session()
    turns = (
        ChatbotQuery.query.filter_by(session_id=chat.session_id)
        .order_by(ChatbotQuery.query_id.asc())
        .all()
    )
    messages = []
    for turn in turns:
        if turn.message:
            messages.append({"role": "user", "text": turn.message})
        if turn.response:
            messages.append({"role": "assistant", "text": turn.response})
    return jsonify(messages=messages)


@bp.route("/support/chat", methods=["POST"])
def support_chat():
    payload = request.get_json(silent=True) or {}
    message = " ".join(str(payload.get("message", "")).split())
    if not message:
        return jsonify(error="Say something and I will answer."), 400
    if len(message) > 500:
        message = message[:500]
    _save_turn("user", message)
    guide_step = session.get("guide_step", 0)
    scripted = reply_to(message, guide_step, use_gemini=False)
    on_tour = scripted.get("guide_step", 0) != guide_step or (
        guide_step and scripted.get("text", "").startswith("No problem")
    )
    if on_tour:
        session["guide_step"] = scripted.get("guide_step", 0)
    else:
        session["guide_step"] = 0

    def sse(payload_row):
        return f"data: {json.dumps(payload_row)}\n\n"

    def events():
        parts = []
        links = []
        try:
            if on_tour:
                parts.append(scripted["text"])
                links = scripted.get("links") or []
                yield sse({"text": scripted["text"]})
            else:
                for chunk in fandom_chat().stream_answer(message):
                    parts.append(chunk)
                    yield sse({"text": chunk})
                links = related_links(message)
        except Exception:
            current_app.logger.exception("Mina stream failed")
            fallback = reply_to(message, guide_step, use_gemini=False)
            parts = [fallback["text"]]
            links = fallback.get("links") or []
            yield sse({"text": fallback["text"]})
        text = "".join(parts).strip()
        if text:
            _save_turn("assistant", text)
        yield sse({"done": True, "links": links})

    return Response(
        stream_with_context(events()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@bp.route("/sitemap")
def sitemap():
    categories = Category.query.order_by(Category.category_id).all()
    return render_template("sitemap.html", categories=categories)


def _map_pins(pins):
    grouped = {}
    for pin in pins:
        if pin["lat"] is None or pin["lng"] is None:
            continue
        grouped.setdefault(pin["city"], []).append(pin)
    markers = []
    for city, items in grouped.items():
        markers.append(
            {
                "city": city,
                "lat": items[0]["lat"],
                "lng": items[0]["lng"],
                "events": [
                    {"id": item["id"], "title": item["title"], "when": item["when"], "kind": item["kind"]}
                    for item in items
                ],
            }
        )
    return markers


@bp.route("/events")
def events():
    city = request.args.get("city", "").strip()
    event_type = request.args.get("event_type", "").strip()
    category = request.args.get("category", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    query = Event.query
    if city:
        query = query.filter(Event.city.ilike(city))
    if event_type:
        query = query.filter(Event.event_type == event_type)
    try:
        if date_from:
            query = query.filter(Event.start_at >= datetime.combine(date.fromisoformat(date_from), datetime.min.time()))
    except ValueError:
        date_from = ""
    try:
        if date_to:
            query = query.filter(Event.start_at < datetime.combine(date.fromisoformat(date_to) + timedelta(days=1), datetime.min.time()))
    except ValueError:
        date_to = ""
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            query = query.filter(Event.category_id == cat.category_id)
        else:
            query = query.filter(Event.event_id == 0)
    rows = query.order_by(Event.start_at.asc()).all()
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    cities = [row[0] for row in db.session.query(Event.city).distinct().order_by(Event.city).all()]
    types = [row[0] for row in db.session.query(Event.event_type).distinct().order_by(Event.event_type).all()]
    pins = []
    for row in rows:
        dist = None
        if lat and lng and row.latitude is not None and row.longitude is not None:
            try:
                dist = round(haversine_km(float(lat), float(lng), row.latitude, row.longitude), 1)
            except ValueError:
                dist = None
        pins.append(
            {
                "id": row.event_id,
                "title": row.title,
                "city": row.city,
                "venue": row.venue,
                "description": row.description,
                "kind": row.event_type,
                "when": row.start_at.strftime("%d %b %Y") if row.start_at else "",
                "ticket_url": row.ticket_url,
                "lat": row.latitude,
                "lng": row.longitude,
                "distance_km": dist,
            }
        )
    if lat and lng:
        pins.sort(key=lambda item: item["distance_km"] if item["distance_km"] is not None else 10**9)
    you = None
    if lat and lng:
        try:
            you = {"lat": float(lat), "lng": float(lng)}
        except ValueError:
            you = None
    viewer = current_user()
    saved_event_ids = set()
    if viewer is not None and viewer.is_member:
        saved_event_ids = {
            row.event_id
            for row in Bookmark.query.filter(Bookmark.user_id == viewer.user_id, Bookmark.event_id.isnot(None))
        }
    focus_event = request.args.get("event", "").strip()
    per_page = 6
    if focus_event.isdigit() and not request.args.get("page"):
        ids = [item["id"] for item in pins]
        if int(focus_event) in ids:
            page = ids.index(int(focus_event)) // per_page + 1
            pages = max(1, (len(pins) + per_page - 1) // per_page)
            shown = pins[(page - 1) * per_page : page * per_page]
        else:
            shown, page, pages, _ = page_of(pins, per_page)
    else:
        shown, page, pages, _ = page_of(pins, per_page)
    event_query = {
        key: value
        for key, value in {
            "city": city,
            "event_type": event_type,
            "category": category,
            "from": date_from,
            "to": date_to,
            "lat": request.args.get("lat", ""),
            "lng": request.args.get("lng", ""),
        }.items()
        if value
    }
    return render_template(
        "events.html",
        events=shown,
        saved_event_ids=saved_event_ids,
        map_pins=_map_pins(pins),
        you=you,
        cities=cities,
        types=types,
        categories=Category.query.order_by(Category.name).all(),
        city=city,
        event_type=event_type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        page=page,
        pages=pages,
        event_query=event_query,
    )


@bp.route("/characters")
def characters():
    category = request.args.get("category", "").strip()
    fandom = request.args.get("fandom", "").strip()
    query = CharacterProfile.query
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            query = query.filter(CharacterProfile.category_id == cat.category_id)
    if fandom:
        fan = Fandom.query.filter_by(slug=fandom, is_active=True).first()
        if fan:
            query = query.filter(CharacterProfile.fandom_id == fan.fandom_id)
        else:
            query = query.filter(CharacterProfile.character_id == 0)
    rows = query.order_by(CharacterProfile.name.asc()).all()
    rows, page, pages, _ = page_of(rows, 12)
    cats = {c.category_id: c for c in Category.query.all()}
    fans = {f.fandom_id: f for f in Fandom.query.all()}
    cards = []
    for row in rows:
        cat = cats.get(row.category_id)
        fan = fans.get(row.fandom_id) if row.fandom_id else None
        cards.append({"row": row, "category": cat, "fandom": fan})
    grouped = {}
    for card in cards:
        label = card["fandom"].name if card["fandom"] else (card["category"].name if card["category"] else "Cast")
        grouped.setdefault(label, []).append(card)
    groups = [{"label": label, "items": grouped[label]} for label in sorted(grouped)]
    return render_template(
        "characters.html",
        cards=cards,
        groups=groups,
        categories=Category.query.order_by(Category.name).all(),
        fandoms=Fandom.query.filter_by(is_active=True).order_by(Fandom.name).all(),
        category=category,
        fandom=fandom,
        page=page,
        pages=pages,
        list_query={key: value for key, value in {"category": category, "fandom": fandom}.items() if value},
    )


@bp.route("/characters/<int:character_id>")
def character_detail(character_id):
    row = db.session.get(CharacterProfile, character_id)
    if row is None:
        abort(404)
    row.view_count = (row.view_count or 0) + 1
    db.session.commit()
    cat = db.session.get(Category, row.category_id)
    fan = db.session.get(Fandom, row.fandom_id) if row.fandom_id else None
    related = (
        Content.query.filter(Content.status == "published", Content.category_id == row.category_id)
        .order_by(Content.popularity_score.desc())
        .limit(4)
        .all()
    )
    saved = None
    viewer = current_user()
    if viewer is not None and viewer.is_member:
        saved = Bookmark.query.filter_by(user_id=viewer.user_id, character_id=row.character_id).first()
    return render_template("character_detail.html", item=row, category=cat, fandom=fan, related=related, saved=saved)


@bp.route("/merchandise")
def merchandise_legacy():
    return redirect(url_for("main.merchandise", **request.args.to_dict(flat=True)))


@bp.route("/merch")
def merchandise():
    category = request.args.get("category", "").strip()
    fandom = request.args.get("fandom", "").strip()
    tag = request.args.get("tag", "").strip()
    upcoming = request.args.get("upcoming", "").strip()
    query = MerchandiseItem.query
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            query = query.filter(MerchandiseItem.category_id == cat.category_id)
    if fandom:
        fan = Fandom.query.filter_by(slug=fandom, is_active=True).first()
        if fan:
            query = query.filter(MerchandiseItem.fandom_id == fan.fandom_id)
        else:
            query = query.filter(MerchandiseItem.item_id == 0)
    if tag:
        named = Tag.query.filter_by(name=tag).first()
        if named is None:
            query = query.filter(MerchandiseItem.item_id == 0)
        else:
            query = query.join(MerchandiseTag, MerchandiseTag.item_id == MerchandiseItem.item_id).filter(MerchandiseTag.tag_id == named.tag_id)
    if upcoming == "yes":
        query = query.filter(MerchandiseItem.is_upcoming.is_(True))
    rows = query.order_by(MerchandiseItem.name.asc()).all()
    rows, page, pages, _ = page_of(rows, 12)
    tag_map = {}
    for link in MerchandiseTag.query.all():
        named_tag = db.session.get(Tag, link.tag_id)
        tag_map.setdefault(link.item_id, []).append(named_tag.name if named_tag else "")
    cats = {c.category_id: c for c in Category.query.all()}
    fans = {f.fandom_id: f for f in Fandom.query.all()}
    cards = [
        {
            "row": row,
            "category": cats.get(row.category_id),
            "fandom": fans.get(row.fandom_id) if row.fandom_id else None,
            "tags": [t for t in tag_map.get(row.item_id, []) if t],
        }
        for row in rows
    ]
    return render_template(
        "merchandise.html",
        cards=cards,
        categories=Category.query.order_by(Category.name).all(),
        fandoms=Fandom.query.filter_by(is_active=True).order_by(Fandom.name).all(),
        tags=Tag.query.order_by(Tag.name).all(),
        category=category,
        fandom=fandom,
        tag=tag,
        upcoming=upcoming == "yes",
        page=page,
        pages=pages,
        list_query={
            key: value
            for key, value in {
                "category": category,
                "fandom": fandom,
                "tag": tag,
                "upcoming": "yes" if upcoming == "yes" else "",
            }.items()
            if value
        },
    )


@bp.route("/upcoming")
def upcoming():
    contents = (
        Content.query.filter(Content.status == "published", Content.release_date.isnot(None), Content.release_date > date.today())
        .order_by(Content.release_date.asc())
        .all()
    )
    merch = MerchandiseItem.query.filter_by(is_upcoming=True).order_by(MerchandiseItem.release_date.asc()).all()
    contents, page, pages, _ = page_of(contents, 8)
    merch, mpage, mpages, _ = page_of(merch, 8, "mpage")
    return render_template(
        "upcoming.html",
        contents=contents,
        merch=merch,
        page=page,
        pages=pages,
        mpage=mpage,
        mpages=mpages,
    )


@bp.route("/merchandise/<int:item_id>")
def merchandise_detail_legacy(item_id):
    return redirect(url_for("main.merchandise_detail", item_id=item_id))


@bp.route("/merch/<int:item_id>")
def merchandise_detail(item_id):
    row = db.session.get(MerchandiseItem, item_id)
    if row is None:
        abort(404)
    row.view_count = (row.view_count or 0) + 1
    db.session.commit()
    tags = []
    for link in MerchandiseTag.query.filter_by(item_id=row.item_id).all():
        tag = db.session.get(Tag, link.tag_id)
        if tag:
            tags.append(tag.name)
    cat = db.session.get(Category, row.category_id)
    saved = None
    viewer = current_user()
    if viewer is not None and viewer.is_member:
        saved = Bookmark.query.filter_by(user_id=viewer.user_id, merchandise_id=row.item_id).first()
    return render_template("merchandise_detail.html", item=row, category=cat, tags=tags, saved=saved)
