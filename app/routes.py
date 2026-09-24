import uuid
from datetime import date

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import and_, func, or_

from .account import current_user
from .events import haversine_km, pin_style
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
    Event,
    Fandom,
    Genre,
    MerchandiseItem,
    MerchandiseTag,
    Tag,
)
from .news import news_items
from .popularity import refresh_content_popularity
from .serialize import rating_summary
from .series import hottest
from .support import reply_to

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

    query = query.filter(Content.status == "published")
    if q:
        like = f"%{q}%"
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

    return query


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
        headlines=news_items()[:4],
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

    return render_template(
        "explore.html",
        items=items,
        categories=categories,
        genres=genres,
        years=years,
        sorts=SORTS,
        sort=sort,
        filters={
            "q": request.args.get("q", "").strip(),
            "category": active_category,
            "genre": request.args.get("genre", "").strip(),
            "year": request.args.get("year", "").strip(),
            "type": request.args.get("type", "").strip(),
            "popularity": request.args.get("popularity", "").strip(),
        },
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
    return render_template(
        "detail.html",
        item=item,
        related=related,
        saved=saved,
        rating=rating_summary(db.session, item.content_id),
        my_score=my_score,
        embed_src=_embed_src(item.embed_url),
    )


def _embed_src(url):
    if not url:
        return None
    if "watch?v=" in url:
        return url.replace("watch?v=", "embed/")
    return url


@bp.route("/news")
def news():
    world = request.args.get("world", "").strip()
    if world not in {"anime", "manga"}:
        world = ""
    items = news_items(world or None)
    return render_template("news.html", items=items, world=world, total=len(news_items()))


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


def _save_turn(role, message):
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
        else:
            db.session.add(ChatbotQuery(session_id=chat.session_id, message="", response=message))
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
    answer = reply_to(message, session.get("guide_step", 0))
    session["guide_step"] = answer.get("guide_step", 0)
    _save_turn("assistant", answer["text"])
    return jsonify(text=answer["text"], links=answer.get("links", []))


@bp.route("/sitemap")
def sitemap():
    categories = Category.query.order_by(Category.category_id).all()
    return render_template("sitemap.html", categories=categories)


@bp.route("/events")
def events():
    city = request.args.get("city", "").strip()
    event_type = request.args.get("event_type", "").strip()
    query = Event.query
    if city:
        query = query.filter(Event.city.ilike(city))
    if event_type:
        query = query.filter(Event.event_type == event_type)
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
                "kind": row.event_type,
                "when": row.start_at.strftime("%d %b %Y") if row.start_at else "",
                "ticket_url": row.ticket_url,
                "style": pin_style(row.latitude, row.longitude),
                "distance_km": dist,
            }
        )
    if lat and lng:
        pins.sort(key=lambda item: item["distance_km"] if item["distance_km"] is not None else 10**9)
    return render_template(
        "events.html",
        events=pins,
        cities=cities,
        types=types,
        city=city,
        event_type=event_type,
    )


@bp.route("/characters")
def characters():
    category = request.args.get("category", "").strip()
    query = CharacterProfile.query
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            query = query.filter(CharacterProfile.category_id == cat.category_id)
    rows = query.order_by(CharacterProfile.name.asc()).all()
    cats = {c.category_id: c for c in Category.query.all()}
    fans = {f.fandom_id: f for f in Fandom.query.all()}
    cards = []
    for row in rows:
        cat = cats.get(row.category_id)
        fan = fans.get(row.fandom_id) if row.fandom_id else None
        cards.append({"row": row, "category": cat, "fandom": fan})
    return render_template("characters.html", cards=cards, categories=Category.query.order_by(Category.name).all(), category=category)


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
def merchandise():
    category = request.args.get("category", "").strip()
    query = MerchandiseItem.query
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            query = query.filter(MerchandiseItem.category_id == cat.category_id)
    rows = query.order_by(MerchandiseItem.name.asc()).all()
    tag_map = {}
    for link in MerchandiseTag.query.all():
        tag = db.session.get(Tag, link.tag_id)
        tag_map.setdefault(link.item_id, []).append(tag.name if tag else "")
    cats = {c.category_id: c for c in Category.query.all()}
    cards = [{"row": row, "category": cats.get(row.category_id), "tags": [t for t in tag_map.get(row.item_id, []) if t]} for row in rows]
    return render_template(
        "merchandise.html",
        cards=cards,
        categories=Category.query.order_by(Category.name).all(),
        category=category,
        upcoming=False,
    )


@bp.route("/upcoming")
def upcoming():
    contents = (
        Content.query.filter(Content.status == "published", Content.release_date.isnot(None), Content.release_date > date.today())
        .order_by(Content.release_date.asc())
        .all()
    )
    merch = MerchandiseItem.query.filter_by(is_upcoming=True).order_by(MerchandiseItem.release_date.asc()).all()
    return render_template("upcoming.html", contents=contents, merch=merch)


@bp.route("/merchandise/<int:item_id>")
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
