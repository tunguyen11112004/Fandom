import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func, or_

from .extensions import db
from .models import (
    ActivityLog,
    Bookmark,
    Category,
    CharacterProfile,
    ChatbotQuery,
    Content,
    ContentGenre,
    ContentRating,
    FanSubmission,
    Feedback,
    Fandom,
    Genre,
    MerchandiseItem,
    Notification,
    User,
    UserCategory,
    UserFandom,
    UserToken,
)
from .popularity import refresh_content_popularity
from .security import hash_password, hash_token, new_raw_token, utcnow, verify_password

bp = Blueprint("account", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        session.pop("user_id", None)
        return None
    user.last_login_at = utcnow()
    db.session.commit()
    return user


def _aware(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _strong(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Za-z]", password)
        and re.search(r"\d", password)
    )


def _issue(user, purpose, hours):
    mapped = "email_verify" if purpose == "verify" else "password_reset"
    UserToken.query.filter_by(user_id=user.user_id, purpose=mapped, used_at=None).update(
        {"used_at": utcnow()}
    )
    raw = new_raw_token()
    token = UserToken(
        user_id=user.user_id,
        purpose=mapped,
        token_hash=hash_token(raw),
        expires_at=utcnow() + timedelta(hours=hours),
    )
    db.session.add(token)
    db.session.commit()
    return raw


def _take(token_value, purpose):
    mapped = "email_verify" if purpose == "verify" else "password_reset"
    row = UserToken.query.filter_by(token_hash=hash_token(token_value), purpose=mapped).first()
    if row is None or row.used_at is not None or _aware(row.expires_at) < datetime.now(timezone.utc):
        return None
    return row


@bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not name or "@" not in email:
            error = "Enter your name and a real email."
        elif password != confirm:
            error = "The two passwords do not match."
        elif not _strong(password):
            error = "Use at least 8 characters, with a letter and a number."
        elif User.query.filter_by(email=email).first():
            error = "That email is already registered. Sign in, or reset the password."
        else:
            user = User(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role="user",
            )
            db.session.add(user)
            db.session.commit()
            token = _issue(user, "verify", 24)
            return redirect(url_for("account.sent", purpose="verify", token=token))
    return render_template("auth/register.html", error=error)


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not verify_password(password, user.password_hash):
            error = "Email or password is not right."
        elif user.locked:
            error = "This account is locked."
        elif user.role == "admin":
            session["user_id"] = user.user_id
            return redirect(url_for("account.admin_home"))
        elif user.role != "user":
            error = "Email or password is not right."
        elif not user.verified:
            error = "Verify your email before signing in."
            session["pending_email"] = user.email
        else:
            session["user_id"] = user.user_id
            nxt = request.form.get("next") or request.args.get("next") or url_for("account.dashboard")
            if not nxt.startswith("/"):
                nxt = url_for("account.dashboard")
            return redirect(nxt)
    return render_template("auth/login.html", error=error)


@bp.route("/resend", methods=["POST"])
def resend():
    email = (request.form.get("email") or session.get("pending_email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if user and not user.verified and not user.locked:
        token = _issue(user, "verify", 24)
        return redirect(url_for("account.sent", purpose="verify", token=token))
    return redirect(url_for("account.sent", purpose="verify"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return redirect(url_for("main.home"))


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        token_value = None
        if user and not user.locked:
            token_value = _issue(user, "reset", 0.5)
        return redirect(url_for("account.sent", purpose="reset", token=token_value or ""))
    return render_template("auth/forgot.html")


@bp.route("/sent")
def sent():
    purpose = request.args.get("purpose", "reset")
    token = request.args.get("token", "")
    link = None
    if token and purpose == "verify":
        link = url_for("account.verify", token=token, _external=False)
    elif token and purpose == "reset":
        link = url_for("account.reset", token=token, _external=False)
    return render_template("auth/sent.html", purpose=purpose, link=link)


@bp.route("/verify/<token>")
def verify(token):
    row = _take(token, "verify")
    if row is None:
        return render_template("auth/sent.html", purpose="expired", link=None)
    row.used_at = utcnow()
    row.user.verified = True
    db.session.commit()
    return redirect(url_for("account.login", next="/profile"))


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    row = _take(token, "reset")
    error = None
    if row is None:
        return render_template("auth/sent.html", purpose="expired", link=None)
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if password != confirm:
            error = "The two passwords do not match."
        elif not _strong(password):
            error = "Use at least 8 characters, with a letter and a number."
        else:
            row.user.password_hash = hash_password(password)
            row.used_at = utcnow()
            row.user.session_version = (row.user.session_version or 1) + 1
            db.session.commit()
            return redirect(url_for("account.login"))
    return render_template("auth/reset.html", error=error, token=token)


def _member():
    user = current_user()
    if user is None or not user.is_member:
        return None
    return user


def _admin():
    user = current_user()
    if user is None or user.role != "admin":
        return None
    return user


def _log_activity(user, kind, summary, href=""):
    db.session.add(
        ActivityLog(
            user_id=user.user_id,
            action=kind[:50],
            entity_type="site",
            details=(summary or "")[:255],
        )
    )


def _admin_log(admin, action, detail):
    db.session.add(
        ActivityLog(
            user_id=admin.user_id,
            action=action[:50],
            entity_type="admin",
            details=(detail or "")[:255],
        )
    )


def _interest_slugs(user):
    rows = (
        db.session.query(Category.slug)
        .join(UserCategory, UserCategory.category_id == Category.category_id)
        .filter(UserCategory.user_id == user.user_id)
        .all()
    )
    return [row[0] for row in rows]


def _set_interests(user, slugs, categories):
    allowed = {category.slug: category.category_id for category in categories}
    UserCategory.query.filter_by(user_id=user.user_id).delete()
    for slug in slugs:
        if slug in allowed:
            db.session.add(UserCategory(user_id=user.user_id, category_id=allowed[slug]))


def _slugify(title, ignore_id=None):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "title"
    slug = base
    number = 2
    while True:
        taken = Content.query.filter_by(slug=slug).first()
        if taken is None or taken.content_id == ignore_id:
            return slug
        slug = f"{base}-{number}"
        number += 1


@bp.route("/dashboard")
def dashboard():
    user = _member()
    if user is None:
        return redirect(url_for("account.login", next=request.path))
    kind = request.args.get("kind", "").strip()
    bookmarks = (
        Bookmark.query.filter_by(user_id=user.user_id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    if kind == "character":
        bookmarks = [row for row in bookmarks if row.character_id]
    elif kind == "merchandise":
        bookmarks = [row for row in bookmarks if row.merchandise_id]
    elif kind:
        bookmarks = [row for row in bookmarks if row.content and row.content.content_type == kind]
    activity = (
        ActivityLog.query.filter_by(user_id=user.user_id)
        .order_by(ActivityLog.log_id.desc())
        .limit(8)
        .all()
    )
    picks = []
    if user.favorite:
        picks = (
            Content.query.filter(
                Content.status == "published",
                Content.title.ilike(f"%{user.favorite}%"),
            )
            .order_by(Content.popularity_score.desc())
            .limit(4)
            .all()
        )
    chosen_slugs = _interest_slugs(user)
    if not picks and chosen_slugs:
        picks = (
            Content.query.join(Category)
            .filter(Content.status == "published", Category.slug.in_(chosen_slugs))
            .order_by(Content.popularity_score.desc())
            .limit(4)
            .all()
        )
    submissions = (
        FanSubmission.query.filter_by(user_id=user.user_id)
        .order_by(FanSubmission.submission_id.desc())
        .all()
    )
    return render_template(
        "auth/dashboard.html",
        user=user,
        bookmarks=bookmarks,
        activity=activity,
        picks=picks,
        submissions=submissions,
        kind=kind,
        categories=Category.query.order_by(Category.category_id).all(),
    )


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if user is None:
        return redirect(url_for("account.login", next=request.path))
    error = None
    categories = Category.query.order_by(Category.category_id).all()
    if request.method == "POST":
        user.name = request.form.get("name", user.name).strip() or user.name
        user.favorite = request.form.get("favorite", "").strip()[:120]
        chosen = request.form.getlist("interests")
        _set_interests(user, chosen, categories)
        UserFandom.query.filter_by(user_id=user.user_id).delete()
        for fid in request.form.getlist("fandoms"):
            if fid.isdigit():
                fan = db.session.get(Fandom, int(fid))
                if fan is not None:
                    db.session.add(UserFandom(user_id=user.user_id, fandom_id=fan.fandom_id))
        theme = request.form.get("theme", "dark")
        font = request.form.get("font", "medium")
        user.theme = theme if theme in {"dark", "light"} else "dark"
        user.font_size = font if font in {"small", "medium", "large"} else "medium"
        upload = request.files.get("avatar")
        if upload and upload.filename:
            ext = upload.filename.rsplit(".", 1)[-1].lower()
            blob = upload.read()
            if ext not in {"png", "jpg", "jpeg", "webp"} or len(blob) > 2_000_000:
                error = "Use a PNG, JPG, or WEBP under 2 MB. Your other changes were kept."
            else:
                folder = os.path.join(current_app.static_folder, "uploads", "avatars")
                os.makedirs(folder, exist_ok=True)
                filename = f"{user.user_id}-{secrets.token_hex(4)}.{ext}"
                with open(os.path.join(folder, filename), "wb") as handle:
                    handle.write(blob)
                user.avatar_path = f"uploads/avatars/{filename}"
        if error is None:
            _log_activity(user, "profile", "Updated profile and display preferences", "/profile")
            db.session.commit()
            return redirect(url_for("account.profile"))
        db.session.commit()
    return render_template(
        "auth/profile.html",
        user=user,
        error=error,
        categories=categories,
        chosen=set(_interest_slugs(user)),
        fandoms=Fandom.query.filter_by(is_active=True).order_by(Fandom.name).all(),
        chosen_fandoms={row.fandom_id for row in UserFandom.query.filter_by(user_id=user.user_id)},
    )


@bp.route("/display", methods=["GET", "POST"])
def display():
    user = current_user()
    if request.method == "POST":
        theme = request.form.get("theme", "dark")
        font = request.form.get("font", "medium")
        theme = theme if theme in {"dark", "light"} else "dark"
        font = font if font in {"small", "medium", "large"} else "medium"
        if user is not None:
            user.theme = theme
            user.font_size = font
            db.session.commit()
        else:
            session["theme"] = theme
            session["font"] = font
        nxt = request.form.get("next") or url_for("account.display")
        if not nxt.startswith("/"):
            nxt = url_for("account.display")
        return redirect(nxt)
    return render_template("auth/display.html", user=user)


@bp.route("/bookmark/<slug>", methods=["POST"])
def bookmark(slug):
    user = _member()
    if user is None:
        return redirect(url_for("account.login", next=f"/explore/{slug}"))
    item = Content.query.filter_by(slug=slug).first()
    if item is None:
        return redirect(url_for("main.explore"))
    row = Bookmark.query.filter_by(user_id=user.user_id, content_id=item.content_id).first()
    action = request.form.get("action", "save")
    if action == "remove" and row is not None:
        db.session.delete(row)
        _log_activity(user, "bookmark", f"Removed {item.title}", f"/explore/{item.slug}")
    elif row is None:
        db.session.add(
            Bookmark(
                user_id=user.user_id,
                content_id=item.content_id,
                note=request.form.get("note", "").strip()[:280],
            )
        )
        _log_activity(user, "bookmark", f"Bookmarked {item.title}", f"/explore/{item.slug}")
    else:
        row.note = request.form.get("note", "").strip()[:280]
    refresh_content_popularity(db.session, item.content_id)
    db.session.commit()
    nxt = request.form.get("next") or url_for("main.content_detail", slug=slug)
    if not nxt.startswith("/"):
        nxt = url_for("account.dashboard")
    return redirect(nxt)


@bp.route("/rate/<slug>", methods=["POST"])
def rate(slug):
    user = _member()
    if user is None:
        return redirect(url_for("account.login", next=f"/explore/{slug}"))
    item = Content.query.filter_by(slug=slug, status="published").first()
    if item is None:
        return redirect(url_for("main.explore"))
    score = request.form.get("score", "")
    if not score.isdigit() or int(score) < 1 or int(score) > 5:
        return redirect(url_for("main.content_detail", slug=slug))
    row = ContentRating.query.filter_by(user_id=user.user_id, content_id=item.content_id).first()
    if row is None:
        db.session.add(ContentRating(user_id=user.user_id, content_id=item.content_id, score=int(score)))
    else:
        row.score = int(score)
    _log_activity(user, "rate", f"Rated {item.title} {score}/5", f"/explore/{item.slug}")
    refresh_content_popularity(db.session, item.content_id)
    db.session.commit()
    return redirect(url_for("main.content_detail", slug=slug))


def _toggle_bookmark(user, *, content_id=None, character_id=None, merchandise_id=None, event_id=None, note="", action="save"):
    q = Bookmark.query.filter_by(user_id=user.user_id)
    if content_id:
        q = q.filter_by(content_id=content_id)
    elif character_id:
        q = q.filter_by(character_id=character_id)
    elif merchandise_id:
        q = q.filter_by(merchandise_id=merchandise_id)
    else:
        q = q.filter_by(event_id=event_id)
    row = q.first()
    if action == "remove" and row is not None:
        db.session.delete(row)
    elif row is None and action != "remove":
        db.session.add(
            Bookmark(
                user_id=user.user_id,
                content_id=content_id,
                character_id=character_id,
                merchandise_id=merchandise_id,
                event_id=event_id,
                note=(note or "")[:280] or None,
            )
        )
    elif row is not None:
        row.note = (note or "")[:280] or None
    db.session.commit()


@bp.route("/bookmark/character/<int:character_id>", methods=["POST"])
def bookmark_character(character_id):
    user = _member()
    if user is None:
        return redirect(url_for("account.login", next=f"/characters/{character_id}"))
    if db.session.get(CharacterProfile, character_id) is None:
        return redirect(url_for("main.characters"))
    _toggle_bookmark(
        user,
        character_id=character_id,
        note=request.form.get("note", ""),
        action=request.form.get("action", "save"),
    )
    return redirect(url_for("main.character_detail", character_id=character_id))


@bp.route("/bookmark/merchandise/<int:item_id>", methods=["POST"])
def bookmark_merchandise(item_id):
    user = _member()
    if user is None:
        return redirect(url_for("account.login", next=f"/merchandise/{item_id}"))
    if db.session.get(MerchandiseItem, item_id) is None:
        return redirect(url_for("main.merchandise"))
    _toggle_bookmark(
        user,
        merchandise_id=item_id,
        note=request.form.get("note", ""),
        action=request.form.get("action", "save"),
    )
    return redirect(url_for("main.merchandise_detail", item_id=item_id))


@bp.route("/bookmark/event/<int:event_id>", methods=["POST"])
def bookmark_event(event_id):
    from .models import Event

    user = _member()
    if user is None:
        return redirect(url_for("account.login", next="/events"))
    if db.session.get(Event, event_id) is None:
        return redirect(url_for("main.events"))
    _toggle_bookmark(user, event_id=event_id, action=request.form.get("action", "save"))
    return redirect(url_for("main.events") + f"#{event_id}")


@bp.route("/submissions", methods=["GET", "POST"])
def submissions():
    user = _member()
    if user is None:
        return redirect(url_for("account.login", next=request.path))
    error = None
    categories = Category.query.order_by(Category.category_id).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        category_id = request.form.get("category_id", "")
        content_type = request.form.get("content_type", "article")
        media_url = request.form.get("media_url", "").strip()
        rights = request.form.get("rights") == "yes"
        category = db.session.get(Category, int(category_id)) if category_id.isdigit() else None
        if not title or not body or category is None:
            error = "Title, category, and the story itself are required."
        elif content_type not in {"article", "video", "image", "profile"}:
            error = "Pick a content type from the list."
        elif media_url and not media_url.startswith(("http://", "https://")):
            error = "Media links need to start with http:// or https://."
        elif not rights:
            error = "Confirm you have the right to share this before it can be queued."
        else:
            row_id = request.form.get("submission_id", "")
            row = None
            if row_id.isdigit():
                row = FanSubmission.query.filter_by(submission_id=int(row_id), user_id=user.user_id).first()
            if row is None:
                row = FanSubmission(user_id=user.user_id, category_id=category.category_id)
                db.session.add(row)
            elif row.status not in {"pending", "rejected"}:
                error = "That piece is already published."
            if error is None:
                row.category_id = category.category_id
                row.title = title[:200]
                row.body = body
                row.content_type = content_type if content_type != "profile" else "article"
                row.media_url = media_url[:300]
                row.rights_ok = True
                row.status = "pending"
                row.reject_reason = ""
                _log_activity(user, "submission", f"Sent “{row.title}” for review", "/dashboard")
                db.session.commit()
                return redirect(url_for("account.dashboard"))
    return render_template(
        "auth/submissions.html",
        user=user,
        error=error,
        categories=categories,
        mine=FanSubmission.query.filter_by(user_id=user.user_id).order_by(FanSubmission.submission_id.desc()).all(),
        edit=FanSubmission.query.filter_by(
            user_id=user.user_id,
            submission_id=int(request.args.get("edit")),
            status="rejected",
        ).first()
        if str(request.args.get("edit", "")).isdigit()
        else None,
    )


@bp.route("/feedback", methods=["GET", "POST"])
def feedback():
    user = current_user()
    error = None
    sent = request.args.get("sent") == "1"
    if request.method == "POST":
        kind = request.form.get("kind", "")
        message = request.form.get("message", "").strip()
        email = request.form.get("email", "").strip().lower()
        page_url = request.form.get("page_url", "").strip()
        steps = request.form.get("steps", "").strip()
        if kind not in {"bug", "suggestion", "query"}:
            error = "Choose bug, suggestion, or question."
        elif not message:
            error = "Write the feedback before sending it."
        elif user is None and "@" not in email:
            error = "Guests need an email so the desk can reply."
        elif kind == "bug" and not steps:
            error = "A bug report needs the steps that show it again."
        else:
            row = Feedback(
                user_id=user.user_id if user else None,
                contact_email=user.email if user else email,
                type=kind,
                subject=kind.capitalize(),
                page_url=page_url[:300] or None,
                reproduction_steps=steps or None,
                message=message,
            )
            db.session.add(row)
            if user and user.is_member:
                _log_activity(user, "feedback", f"Sent a {kind}", "/feedback")
            db.session.commit()
            return redirect(url_for("account.feedback", sent=1))
    return render_template("auth/feedback.html", user=user, error=error, sent=sent)


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if (
            user is None
            or user.role != "admin"
            or user.locked
            or not verify_password(password, user.password_hash)
        ):
            error = "Admin sign-in was refused."
        else:
            session["user_id"] = user.user_id
            return redirect(url_for("account.admin_home"))
    return render_template("auth/admin_login.html", error=error)


@bp.route("/admin")
def admin_home():
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    days = request.args.get("days", "30")
    since = None
    if days in {"7", "30"}:
        since = datetime.now(timezone.utc) - timedelta(days=int(days))
    active_query = User.query.filter(User.role == "user", User.last_login_at.isnot(None))
    chat_query = ChatbotQuery.query
    if since is not None:
        active_query = active_query.filter(User.last_login_at >= since)
        chat_query = chat_query.filter(ChatbotQuery.created_at >= since)
    popular = (
        db.session.query(Category.name, func.count(Content.content_id))
        .join(Content, Content.category_id == Category.category_id)
        .group_by(Category.category_id)
        .order_by(func.count(Content.content_id).desc())
        .all()
    )
    members = User.query.filter_by(role="user").order_by(User.name).all()
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        members = (
            User.query.filter(User.role == "user")
            .filter(or_(User.name.ilike(like), User.email.ilike(like)))
            .order_by(User.name)
            .all()
        )
    tab = request.args.get("tab", "queue")
    if tab not in {"queue", "feedback", "health", "content", "categories", "users", "record"}:
        tab = "queue"
    return render_template(
        "auth/admin.html",
        user=user,
        tab=tab,
        days=days,
        active_users=active_query.count(),
        member_count=User.query.filter_by(role="user").count(),
        chat_count=chat_query.count(),
        popular=popular,
        titles=Content.query.order_by(Content.title).all(),
        categories=Category.query.order_by(Category.category_id).all(),
        members=members,
        queue=FanSubmission.query.filter_by(status="pending").order_by(FanSubmission.submission_id.asc()).all(),
        feedback_rows=_feedback_rows(),
        logs=ActivityLog.query.filter_by(entity_type="admin").order_by(ActivityLog.log_id.desc()).limit(12).all(),
        submission_counts=dict(
            db.session.query(FanSubmission.user_id, func.count(FanSubmission.submission_id))
            .group_by(FanSubmission.user_id)
            .all()
        ),
        query=q,
        kinds=request.args.get("kind", ""),
        states=request.args.get("status", ""),
        open_feedback=Feedback.query.filter(Feedback.status.in_(["new", "in_progress"])).count(),
        title_count=Content.query.count(),
    )


def _feedback_rows():
    query = Feedback.query
    kind = request.args.get("kind", "").strip()
    status = request.args.get("status", "").strip()
    if kind in {"bug", "suggestion", "query"}:
        query = query.filter_by(type=kind)
    mapped = {"reviewing": "in_progress", "done": "resolved"}.get(status, status)
    if mapped in {"new", "in_progress", "resolved", "closed"}:
        query = query.filter_by(status=mapped)
    return query.order_by(Feedback.feedback_id.desc()).all()


def _content_from_form(item):
    title = request.form.get("title", "").strip()
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0))
    content_type = request.form.get("content_type", "article")
    genre = request.form.get("genre", "").strip()
    year = request.form.get("release_year", "").strip()
    summary = request.form.get("summary", "").strip()
    body = request.form.get("body", "").strip()
    embed = request.form.get("embed_url", "").strip()
    tags = request.form.get("tags", "").strip()
    if not title or category is None or not genre or not summary or not body or not year.isdigit():
        return "Title, category, genre, year, summary, and body are required."
    if content_type not in {"article", "video", "audio", "image", "trailer", "explainer"}:
        content_type = "article"
    if embed and not embed.startswith(("http://", "https://")):
        return "Embed links need to start with http:// or https://."
    item.category_id = category.category_id
    item.title = title[:200]
    item.slug = item.slug or _slugify(title)
    if request.form.get("retitle") == "yes":
        item.slug = _slugify(title, item.content_id)
    item.content_type = content_type
    item.release_year = int(year)
    item.summary = summary[:500]
    item.body = body
    item.embed_url = embed[:300]
    item.featured = request.form.get("featured") == "yes"
    item.published = request.form.get("published") == "yes"
    score = request.form.get("popularity_score", "50")
    item.popularity_score = int(score) if score.isdigit() else 50
    db.session.flush()
    ContentGenre.query.filter_by(content_id=item.content_id).delete()
    named = Genre.query.filter_by(name=genre[:60]).first()
    if named is None:
        named = Genre(name=genre[:60])
        db.session.add(named)
        db.session.flush()
    db.session.add(ContentGenre(content_id=item.content_id, genre_id=named.genre_id))
    return None


@bp.route("/admin/content", methods=["POST"])
def admin_content_create():
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    item = Content(slug="pending", category_id=1, title="pending", type="article", summary="", body="", release_date=date(2026, 1, 1))
    error = _content_from_form(item)
    if error:
        return redirect(url_for("account.admin_home", tab="content", error=error))
    item.slug = _slugify(item.title)
    db.session.add(item)
    _admin_log(user, "content.create", item.title)
    db.session.commit()
    return redirect(url_for("account.admin_home", tab="content"))


@bp.route("/admin/content/<int:item_id>", methods=["POST"])
def admin_content_update(item_id):
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    item = db.session.get(Content, item_id)
    if item is None:
        return redirect(url_for("account.admin_home"))
    if request.form.get("action") == "hide":
        item.published = False
        _admin_log(user, "content.hide", item.title)
        db.session.commit()
        return redirect(url_for("account.admin_home", tab="content"))
    error = _content_from_form(item)
    if error is None:
        _admin_log(user, "content.edit", item.title)
        db.session.commit()
    return redirect(url_for("account.admin_home", tab="content"))


@bp.route("/admin/category/<int:category_id>", methods=["POST"])
def admin_category(category_id):
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    category = db.session.get(Category, category_id)
    if category is not None:
        category.description = request.form.get("description", category.description).strip() or category.description
        _admin_log(user, "category.edit", category.name)
        db.session.commit()
    return redirect(url_for("account.admin_home", tab="categories"))


@bp.route("/admin/users/<int:user_id>", methods=["POST"])
def admin_user(user_id):
    admin = _admin()
    if admin is None:
        return redirect(url_for("account.admin_login"))
    member = db.session.get(User, user_id)
    if member is not None and member.role == "user":
        member.locked = request.form.get("locked") == "yes"
        if member.locked:
            member.session_version = (member.session_version or 1) + 1
        _admin_log(admin, "user.lock" if member.locked else "user.unlock", member.email)
        db.session.commit()
    return redirect(url_for("account.admin_home", tab="users"))


@bp.route("/admin/submissions/<int:submission_id>", methods=["POST"])
def admin_submission(submission_id):
    admin = _admin()
    if admin is None:
        return redirect(url_for("account.admin_login"))
    row = db.session.get(FanSubmission, submission_id)
    if row is None:
        return redirect(url_for("account.admin_home", tab="queue"))
    decision = request.form.get("decision")
    if decision == "approve":
        item = Content(
            category_id=row.category_id,
            title=row.title,
            slug=_slugify(row.title),
            type=row.content_type if row.content_type in {"article", "video", "image"} else "article",
            summary=(row.body or "")[:180],
            body=row.body,
            embed_url=row.media_url,
            popularity_score=40,
            status="published",
            rights_confirmed=True,
        )
        item.release_year = datetime.now(timezone.utc).year
        db.session.add(item)
        row.status = "approved"
        row.reject_reason = ""
        db.session.add(
            Notification(
                user_id=row.user_id,
                title="Your piece was published",
                body=f"“{row.title}” is now on the shelves.",
            )
        )
        _admin_log(admin, "submission.approve", row.title)
    elif decision == "reject":
        reason = request.form.get("reason", "").strip() or "Needs a revision."
        row.status = "rejected"
        row.reject_reason = reason[:300]
        db.session.add(
            Notification(
                user_id=row.user_id,
                title="Your piece needs a revision",
                body=row.reject_reason,
            )
        )
        _admin_log(admin, "submission.reject", f"{row.title}: {row.reject_reason}")
    db.session.commit()
    return redirect(url_for("account.admin_home", tab="queue"))


@bp.route("/admin/feedback/<int:feedback_id>", methods=["POST"])
def admin_feedback(feedback_id):
    admin = _admin()
    if admin is None:
        return redirect(url_for("account.admin_login"))
    row = db.session.get(Feedback, feedback_id)
    if row is None:
        return redirect(url_for("account.admin_home", tab="feedback"))
    if request.form.get("action") == "delete":
        _admin_log(admin, "feedback.delete", row.email)
        db.session.delete(row)
    else:
        status = request.form.get("status", row.status)
        status = {"reviewing": "in_progress", "done": "resolved"}.get(status, status)
        if status in {"new", "in_progress", "resolved", "closed"}:
            row.status = status
        row.admin_note = request.form.get("admin_note", "").strip()[:300]
        _admin_log(admin, "feedback.update", f"{row.kind} → {row.status}")
    db.session.commit()
    return redirect(url_for("account.admin_home", tab="feedback"))
