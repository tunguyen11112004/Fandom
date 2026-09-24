import uuid

from flask import Blueprint, abort, jsonify, render_template, request, session
from sqlalchemy import func, or_

from . import db
from .account import current_user
from .models import Activity, Bookmark, Category, ChatTurn, Content
from .news import news_items
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

    query = query.filter(Content.published.is_(True))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Content.title.ilike(like),
                Content.summary.ilike(like),
                Content.genre.ilike(like),
            )
        )
    if category:
        query = query.filter(Category.slug == category)
    if genre:
        query = query.filter(Content.genre == genre)
    if year.isdigit():
        query = query.filter(Content.release_year == int(year))
    if content_type:
        query = query.filter(Content.content_type == content_type)
    if popularity in POPULARITY_BANDS:
        low, high = POPULARITY_BANDS[popularity]
        query = query.filter(Content.popularity_score.between(low, high))

    return query


def _apply_sort(query, sort):
    if sort == "popular":
        return query.order_by(Content.popularity_score.desc(), Content.title.asc())
    if sort == "alpha":
        return query.order_by(func.lower(Content.title).asc())
    return query.order_by(Content.release_year.desc(), Content.title.asc())


@bp.route("/")
def home():
    categories = Category.query.order_by(Category.id).all()
    counts = dict(
        db_counts()
    )
    return render_template(
        "home.html",
        categories=categories,
        counts=counts,
        total=Content.query.count(),
        headlines=news_items()[:4],
        hottest=hottest(limit=None),
    )


def db_counts():
    rows = (
        Category.query.outerjoin(Content)
        .with_entities(Category.slug, func.count(Content.id))
        .group_by(Category.id)
        .all()
    )
    return rows


@bp.route("/explore")
def explore():
    sort = request.args.get("sort", "latest")
    if sort not in SORTS:
        sort = "latest"

    query = _apply_sort(
        _apply_filters(Content.query.join(Category), request.args),
        sort,
    )
    items = query.all()
    categories = Category.query.order_by(Category.name).all()
    genres = [
        row[0]
        for row in Content.query.with_entities(Content.genre)
        .distinct()
        .order_by(Content.genre)
        .all()
    ]
    years = [
        row[0]
        for row in Content.query.with_entities(Content.release_year)
        .distinct()
        .order_by(Content.release_year.desc())
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
    )


@bp.route("/explore/<slug>")
def content_detail(slug):
    item = Content.query.filter_by(slug=slug).first()
    viewer = current_user()
    if item is None or (not item.published and (viewer is None or viewer.role != "admin")):
        abort(404)
    item.view_count = (item.view_count or 0) + 1
    saved = None
    if viewer is not None and viewer.role == "member":
        saved = Bookmark.query.filter_by(user_id=viewer.id, content_id=item.id).first()
        db.session.add(
            Activity(
                user_id=viewer.id,
                kind="view",
                summary=f"Opened {item.title}",
                href=f"/explore/{item.slug}",
            )
        )
    db.session.commit()
    related = (
        Content.query.filter(
            Content.category_id == item.category_id,
            Content.id != item.id,
            Content.published.is_(True),
        )
        .order_by(Content.popularity_score.desc())
        .limit(3)
        .all()
    )
    return render_template("detail.html", item=item, related=related, saved=saved)


@bp.route("/news")
def news():
    world = request.args.get("world", "").strip()
    if world not in {"anime", "manga"}:
        world = ""
    items = news_items(world or None)
    return render_template("news.html", items=items, world=world, total=len(news_items()))


def _session_id():
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]


def _save_turn(role, message):
    db.session.add(ChatTurn(session_id=_session_id(), role=role, message=message))
    db.session.commit()


@bp.route("/support/history")
def support_history():
    turns = (
        ChatTurn.query.filter_by(session_id=_session_id())
        .order_by(ChatTurn.id.asc())
        .all()
    )
    return jsonify(
        messages=[{"role": turn.role, "text": turn.message} for turn in turns]
    )


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
    categories = Category.query.order_by(Category.id).all()
    return render_template("sitemap.html", categories=categories)


@bp.route("/events")
def events():
    from .events import EVENTS

    return render_template("events.html", events=EVENTS)


@bp.app_errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404
