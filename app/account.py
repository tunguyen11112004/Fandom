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
from sqlalchemy.exc import IntegrityError

from .config import settings
from .emailer import send_reset_email, send_verify_email
from .extensions import db
from .models import (
    ActivityLog,
    Bookmark,
    Category,
    CharacterProfile,
    ChatbotFaq,
    ChatbotQuery,
    Content,
    ContentGenre,
    ContentTag,
    ContentRating,
    ContentTimelineEntry,
    Event,
    FanSubmission,
    Feedback,
    Fandom,
    Genre,
    Tag,
    MerchandiseItem,
    MerchandiseTag,
    Notification,
    User,
    UserCategory,
    UserFandom,
    UserToken,
)
from .popularity import refresh_content_popularity
from .security import hash_password, hash_token, new_raw_token, utcnow, verify_password

bp = Blueprint("account", __name__)


def _safe_next(value, fallback):
    nxt = (value or "").strip()
    if not nxt.startswith("/") or nxt.startswith("//") or "\\" in nxt:
        return fallback
    return nxt


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


def _issue(user, purpose, hours, raw=None):
    mapped = "email_verify" if purpose == "verify" else "password_reset"
    UserToken.query.filter_by(user_id=user.user_id, purpose=mapped, used_at=None).update(
        {"used_at": utcnow()}
    )
    raw = raw or new_raw_token()
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
    name = ""
    email = ""
    password = ""
    confirm = ""
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
            token = _issue(user, "verify", settings.email_verify_hours)
            try:
                send_verify_email(user.email, token)
            except Exception:
                current_app.logger.exception("verification email failed")
            session["pending_email"] = user.email
            target = {"purpose": "verify"}
            if settings.email_backend != "smtp":
                target["token"] = token
            return redirect(url_for("account.sent", **target))
    return render_template(
        "auth/register.html",
        error=error,
        name=name,
        email=email,
        password=password,
        confirm=confirm,
    )


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
            nxt = _safe_next(request.form.get("next") or request.args.get("next"), url_for("main.home"))
            return redirect(nxt)
    return render_template("auth/login.html", error=error)


@bp.route("/resend", methods=["POST"])
def resend():
    email = (request.form.get("email") or session.get("pending_email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if user and not user.verified and not user.locked:
        token = _issue(user, "verify", settings.email_verify_hours)
        try:
            send_verify_email(user.email, token)
        except Exception:
            current_app.logger.exception("verification email failed")
        target = {"purpose": "verify"}
        if settings.email_backend != "smtp":
            target["token"] = token
        return redirect(url_for("account.sent", **target))
    return redirect(url_for("account.sent", purpose="verify"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return redirect(url_for("main.home"))


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    error = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if "@" not in email:
            error = "Enter the email on the account."
        else:
            user = User.query.filter_by(email=email).first()
            token = ""
            if user and not user.locked:
                token = _issue(user, "reset", settings.password_reset_minutes / 60)
                try:
                    send_reset_email(user.email, token)
                except Exception:
                    current_app.logger.exception("reset email failed")
            target = {"purpose": "reset"}
            if token and settings.email_backend != "smtp":
                target["token"] = token
            return redirect(url_for("account.sent", **target))
    return render_template("auth/forgot.html", error=error, email=email)


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
    score = (request.form.get("score") or "5").strip()
    back = request.form.get("next") or ""
    if not score.isdigit() or int(score) < 1 or int(score) > 5:
        return redirect(back if back.startswith("/media/") else url_for("main.content_detail", slug=slug))
    row = ContentRating.query.filter_by(user_id=user.user_id, content_id=item.content_id).first()
    if row is None:
        db.session.add(ContentRating(user_id=user.user_id, content_id=item.content_id, score=int(score)))
    else:
        row.score = int(score)
    _log_activity(user, "rate", f"Rated {item.title} {score}/5", f"/explore/{item.slug}")
    refresh_content_popularity(db.session, item.content_id)
    db.session.commit()
    if back.startswith("/media/"):
        return redirect(back)
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
    fandoms = Fandom.query.filter_by(is_active=True).order_by(Fandom.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        category_id = request.form.get("category_id", "")
        content_type = request.form.get("content_type", "article")
        media_url = request.form.get("media_url", "").strip()
        rights = request.form.get("rights") == "yes"
        category = db.session.get(Category, int(category_id)) if category_id.isdigit() else None
        file_types = {"video": {".mp4", ".webm"}, "audio": {".mp3", ".wav", ".m4a", ".ogg"}}
        uploaded, upload_error = (None, None)
        if content_type in file_types:
            uploaded, upload_error = _save_media_file(request.files.get("media_file"), file_types[content_type])
        raw_fandom = request.form.get("fandom_id", "").strip()
        fan = db.session.get(Fandom, int(raw_fandom)) if raw_fandom.isdigit() else None
        if not title or not body or category is None or fan is None:
            error = "Title, category, fandom, and the story itself are required."
        elif fan.category_id != category.category_id or not fan.is_active:
            error = "Choose an active fandom in that category."
        elif content_type not in {"article", "video", "audio", "image", "profile"}:
            error = "Pick a content type from the list."
        elif upload_error:
            error = upload_error
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
                row.fandom_id = fan.fandom_id
                row.title = title[:200]
                row.body = body
                row.content_type = content_type if content_type != "profile" else "article"
                row.media_url = (uploaded or media_url)[:300]
                row.rights_ok = True
                row.status = "pending"
                row.reject_reason = ""
                _log_activity(user, "submission", f"Sent “{row.title}” for review", "/dashboard")
                db.session.commit()
                return redirect(url_for("account.dashboard"))
    rejected = FanSubmission.query.filter_by(user_id=user.user_id, status="rejected")
    edit = None
    if request.args.get("new") != "1":
        raw_edit = request.args.get("edit", "")
        if not str(raw_edit).isdigit() and request.method == "POST":
            raw_edit = request.form.get("submission_id", "")
        if str(raw_edit).isdigit():
            edit = rejected.filter_by(submission_id=int(raw_edit)).first()
            if edit is None:
                edit = FanSubmission.query.filter_by(
                    user_id=user.user_id, submission_id=int(raw_edit), status="pending"
                ).first()
        elif request.method == "GET":
            edit = rejected.order_by(FanSubmission.submission_id.desc()).first()
    return render_template(
        "auth/submissions.html",
        user=user,
        error=error,
        categories=categories,
        fandoms=fandoms,
        mine=FanSubmission.query.filter_by(user_id=user.user_id).order_by(FanSubmission.submission_id.desc()).all(),
        edit=edit,
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
    tabs = {
        "queue", "feedback", "health", "content", "categories", "fandoms",
        "characters", "merchandise", "events", "tags", "faqs", "users", "record",
    }
    if tab not in tabs:
        tab = "queue"
    catalog_q = request.args.get("q", "").strip() if tab == "content" else ""
    catalog_category = request.args.get("category", "").strip() if tab == "content" else ""
    catalog_type = request.args.get("type", "").strip() if tab == "content" else ""
    catalog_state = request.args.get("state", "").strip() if tab == "content" else ""
    catalog_featured = request.args.get("featured", "").strip() if tab == "content" else ""
    title_query = Content.query
    if catalog_q:
        like = f"%{catalog_q}%"
        title_query = title_query.filter(or_(Content.title.ilike(like), Content.summary.ilike(like)))
    if catalog_category:
        title_query = title_query.join(Category, Category.category_id == Content.category_id).filter(Category.slug == catalog_category)
    if catalog_type:
        title_query = title_query.filter(Content.type == catalog_type)
    if catalog_state == "live":
        title_query = title_query.filter(Content.status == "published")
    elif catalog_state == "hidden":
        title_query = title_query.filter(Content.status != "published")
    if catalog_featured == "yes":
        title_query = title_query.filter(Content.is_featured.is_(True))
    catalog_page = 1
    catalog_pages = 1
    catalog_total = 0
    titles = []
    if tab == "content":
        catalog_total = title_query.count()
        catalog_pages = max(1, (catalog_total + 7) // 8)
        raw_page = request.args.get("page", "1")
        catalog_page = int(raw_page) if raw_page.isdigit() and int(raw_page) > 0 else 1
        catalog_page = min(catalog_page, catalog_pages)
        titles = title_query.order_by(Content.title).offset((catalog_page - 1) * 8).limit(8).all()
    needs_fandoms = tab in {"content", "fandoms", "characters", "merchandise", "events"}
    return render_template(
        "auth/admin.html",
        user=user,
        tab=tab,
        days=days,
        active_users=active_query.count(),
        member_count=User.query.filter_by(role="user").count(),
        chat_count=chat_query.count(),
        popular=popular,
        titles=titles,
        catalog_page=catalog_page,
        catalog_pages=catalog_pages,
        catalog_total=catalog_total,
        catalog_q=catalog_q,
        catalog_category=catalog_category,
        catalog_type=catalog_type,
        catalog_state=catalog_state,
        catalog_featured=catalog_featured,
        fandom_rows=Fandom.query.order_by(Fandom.name).all() if needs_fandoms else [],
        character_rows=CharacterProfile.query.order_by(CharacterProfile.name).all() if tab == "characters" else [],
        merch_rows=MerchandiseItem.query.order_by(MerchandiseItem.name).all() if tab == "merchandise" else [],
        merch_tag_map=_merch_tag_map() if tab == "merchandise" else {},
        event_rows=Event.query.order_by(Event.start_at.desc()).all() if tab == "events" else [],
        tag_rows=Tag.query.order_by(Tag.name).all() if tab in {"tags", "merchandise"} else [],
        faq_rows=ChatbotFaq.query.order_by(ChatbotFaq.faq_id.desc()).all() if tab == "faqs" else [],
        missed_questions=_missed_questions() if tab == "faqs" else [],
        viewed_titles=Content.query.order_by(Content.view_count.desc()).limit(5).all() if tab == "health" else [],
        viewed_merch=MerchandiseItem.query.order_by(MerchandiseItem.view_count.desc()).limit(5).all() if tab == "health" else [],
        categories=Category.query.order_by(Category.category_id).all(),
        category_usage=_category_usage() if tab == "categories" else {},
        error=request.args.get("error", ""),
        focus=request.args.get("focus", ""),
        draft_name=request.args.get("name", ""),
        draft_description=request.args.get("description", ""),
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


def _save_media_file(upload, allowed=None):
    if upload is None or not upload.filename:
        return None, None
    ext = os.path.splitext(upload.filename)[1].lower()
    allowed = allowed or {".mp4", ".webm", ".mp3", ".wav", ".m4a", ".ogg"}
    if ext not in allowed:
        names = ", ".join(item[1:] for item in sorted(allowed))
        return None, f"Upload a {names} file."
    upload.seek(0, os.SEEK_END)
    size = upload.tell()
    upload.seek(0)
    if size > 30 * 1024 * 1024:
        return None, "Media files must be 30 MB or smaller."
    folder = os.path.join(current_app.static_folder, "uploads", "media")
    os.makedirs(folder, exist_ok=True)
    filename = f"{secrets.token_hex(16)}{ext}"
    upload.save(os.path.join(folder, filename))
    return f"/static/uploads/media/{filename}", None


def _apply_media(item, content_type, embed, uploaded):
    needs_media = content_type in {"video", "audio", "trailer", "explainer"}
    if request.form.get("remove_media") == "yes" and not uploaded and not embed:
        item.embed_url = None
        item.media_url = None
        if needs_media:
            return "Add a YouTube link or upload a video or audio file."
        return None
    if uploaded:
        item.embed_url = uploaded
        item.media_url = uploaded
        return None
    if embed:
        item.embed_url = embed[:500]
        item.media_url = embed[:500]
        return None
    existing = item.embed_url if item.embed_url and item.embed_url != "None" else None
    if existing:
        item.embed_url = existing
        return None
    if needs_media:
        return "Add a YouTube link or upload a video or audio file."
    return None


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
    uploaded, upload_error = _save_media_file(request.files.get("media_file"))
    if upload_error:
        return upload_error
    if embed and not embed.startswith(("http://", "https://")):
        return "Video and audio links need to start with http:// or https://."
    raw_fandom = request.form.get("fandom_id", "").strip()
    fan = db.session.get(Fandom, int(raw_fandom)) if raw_fandom.isdigit() else None
    if raw_fandom and (fan is None or fan.category_id != category.category_id or not fan.is_active):
        return "Choose an active fandom in that category."
    item.category_id = category.category_id
    item.fandom_id = fan.fandom_id if fan else None
    item.title = title[:200]
    item.slug = item.slug or _slugify(title)
    if request.form.get("retitle") == "yes":
        item.slug = _slugify(title, item.content_id)
    item.content_type = content_type
    item.release_year = int(year)
    item.summary = summary[:500]
    item.body = body
    media_error = _apply_media(item, content_type, embed, uploaded)
    if media_error:
        return media_error
    item.featured = request.form.get("featured") == "yes"
    item.published = request.form.get("published") == "yes"
    score = request.form.get("popularity_score", "50")
    item.popularity_score = int(score) if score.isdigit() else 50
    db.session.add(item)
    db.session.flush()
    ContentGenre.query.filter_by(content_id=item.content_id).delete()
    named = Genre.query.filter_by(name=genre[:60]).first()
    if named is None:
        named = Genre(name=genre[:60])
        db.session.add(named)
        db.session.flush()
    db.session.add(ContentGenre(content_id=item.content_id, genre_id=named.genre_id))
    if "tags" in request.form:
        item.tags = tags
    _sync_timeline(item)
    return None


def _sync_timeline(item):
    if "timeline" not in request.form:
        return
    ContentTimelineEntry.query.filter_by(content_id=item.content_id).delete()
    order = 0
    for line in request.form.get("timeline", "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        year = parts[0] if len(parts) > 1 else ""
        title = parts[1] if len(parts) > 1 else parts[0]
        description = parts[2] if len(parts) > 2 else ""
        if not title:
            continue
        entry_date = date(int(year), 1, 1) if year.isdigit() and len(year) == 4 else None
        db.session.add(
            ContentTimelineEntry(
                content_id=item.content_id,
                entry_date=entry_date,
                title=title[:200],
                description=description or None,
                sort_order=order,
            )
        )
        order += 1


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
    if error:
        db.session.rollback()
        return redirect(url_for("account.admin_home", tab="content", error=error, focus=item_id))
    _admin_log(user, "content.edit", item.title)
    db.session.commit()
    return redirect(url_for("account.admin_home", tab="content"))


def _category_redirect(error=None, **extra):
    params = {"tab": "categories"}
    if error:
        params["error"] = error
    params.update({key: value for key, value in extra.items() if value})
    return redirect(url_for("account.admin_home", **params))


def _category_usage():
    def grouped(model):
        rows = db.session.query(model.category_id, func.count()).group_by(model.category_id).all()
        return {category_id: count for category_id, count in rows if category_id}

    titles = grouped(Content)
    fandoms = grouped(Fandom)
    characters = grouped(CharacterProfile)
    merchandise = grouped(MerchandiseItem)
    submissions = grouped(FanSubmission)
    usage = {}
    for category_id in set(titles) | set(fandoms) | set(characters) | set(merchandise) | set(submissions):
        entry = {
            "titles": titles.get(category_id, 0),
            "fandoms": fandoms.get(category_id, 0),
            "characters": characters.get(category_id, 0),
            "merchandise": merchandise.get(category_id, 0),
            "submissions": submissions.get(category_id, 0),
        }
        entry["reason"] = _category_block(entry)
        usage[category_id] = entry
    return usage


def _category_block(usage):
    labels = (
        ("titles", "title", "titles"),
        ("fandoms", "fandom", "fandoms"),
        ("characters", "character", "characters"),
        ("merchandise", "merchandise item", "merchandise items"),
        ("submissions", "submission", "submissions"),
    )
    parts = []
    for key, singular, plural in labels:
        count = usage.get(key, 0)
        if count:
            parts.append(f"{count} {singular if count == 1 else plural}")
    if not parts:
        return None
    return "This category still has " + ", ".join(parts) + ". Move or remove them before deleting it."


def _validate_category(name, description, ignore_id=None):
    name = " ".join((name or "").split())
    description = (description or "").strip()
    if not name:
        return "Category name is required."
    if len(name) < 2 or len(name) > 50:
        return "Category name must be 2 to 50 characters."
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &'./-]*", name) is None:
        return "Category name can use letters, numbers, spaces, and & ' . / -."
    if len(description) > 500:
        return "Description must be 500 characters or fewer."
    clash = Category.query.filter(func.lower(Category.name) == name.lower()).first()
    if clash is not None and clash.category_id != ignore_id:
        return "A category with that name already exists."
    return None


def _category_slug(name, ignore_id=None):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "category"
    base = base[:60].strip("-") or "category"
    slug = base
    number = 2
    while True:
        taken = Category.query.filter_by(slug=slug).first()
        if taken is None or taken.category_id == ignore_id:
            return slug
        suffix = f"-{number}"
        slug = f"{base[: 60 - len(suffix)].strip('-')}{suffix}"
        number += 1


@bp.route("/admin/categories", methods=["POST"])
def admin_category_create():
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    name = request.form.get("name", "")
    description = request.form.get("description", "")
    error = _validate_category(name, description)
    if error:
        return _category_redirect(error, name=name.strip(), description=description.strip())
    clean = " ".join(name.split())
    row = Category(
        name=clean,
        slug=_category_slug(clean),
        description=description.strip() or None,
    )
    db.session.add(row)
    _admin_log(user, "category.create", clean)
    db.session.commit()
    return _category_redirect()


@bp.route("/admin/category/<int:category_id>", methods=["POST"])
def admin_category(category_id):
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    category = db.session.get(Category, category_id)
    if category is None:
        return _category_redirect("That category no longer exists.")
    name = request.form.get("name", "")
    description = request.form.get("description", "")
    error = _validate_category(name, description, ignore_id=category.category_id)
    if error:
        return _category_redirect(error, focus=category_id, name=name.strip(), description=description.strip())
    category.name = " ".join(name.split())
    category.description = description.strip() or None
    _admin_log(user, "category.edit", category.name)
    db.session.commit()
    return _category_redirect()


@bp.route("/admin/category/<int:category_id>/delete", methods=["POST"])
def admin_category_delete(category_id):
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    category = db.session.get(Category, category_id)
    if category is None:
        return _category_redirect("That category no longer exists.")
    blocked = _category_block(_category_usage().get(category_id, {}))
    if blocked:
        return _category_redirect(blocked, focus=category_id)
    name = category.name
    db.session.delete(category)
    _admin_log(user, "category.delete", name)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _category_redirect("This category is still in use. Move or remove what belongs to it first.", focus=category_id)
    return _category_redirect()


def _desk_redirect(tab, error=None, focus=None):
    params = {"tab": tab}
    if error:
        params["error"] = error
    if focus is not None:
        params["focus"] = focus
    return redirect(url_for("account.admin_home", **params))


def _require_admin():
    user = _admin()
    if user is None:
        return None, redirect(url_for("account.admin_login"))
    return user, None


def _clean_name(value, low, high, label):
    name = " ".join((value or "").split())
    if not name:
        return None, f"{label} is required."
    if len(name) < low or len(name) > high:
        return None, f"{label} must be {low} to {high} characters."
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &'./-]*", name) is None:
        return None, f"{label} can use letters, numbers, spaces, and & ' . / -."
    return name, None


def _optional_text(value, limit, label):
    text = (value or "").strip()
    if len(text) > limit:
        return None, f"{label} must be {limit} characters or fewer."
    return text or None, None


def _optional_url(value, label):
    text = (value or "").strip()
    if not text:
        return None, None
    if not text.startswith(("http://", "https://")):
        return None, f"{label} must start with http:// or https://."
    if len(text) > 500:
        return None, f"{label} must be 500 characters or fewer."
    return text, None


def _named_slug(model, name, ignore_id=None, id_attr="fandom_id", max_len=140):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "item"
    base = base[:max_len].strip("-") or "item"
    slug = base
    number = 2
    while True:
        taken = model.query.filter_by(slug=slug).first()
        if taken is None or getattr(taken, id_attr) == ignore_id:
            return slug
        suffix = f"-{number}"
        slug = f"{base[: max_len - len(suffix)].strip('-')}{suffix}"
        number += 1


def _fandom_in_use(fandom_id):
    return any(
        (
            Content.query.filter_by(fandom_id=fandom_id).first(),
            CharacterProfile.query.filter_by(fandom_id=fandom_id).first(),
            MerchandiseItem.query.filter_by(fandom_id=fandom_id).first(),
            Event.query.filter_by(fandom_id=fandom_id).first(),
        )
    )


def _merch_tag_map():
    grouped = {}
    for link in MerchandiseTag.query.all():
        grouped.setdefault(link.item_id, set()).add(link.tag_id)
    return grouped


def _missed_questions():
    rows = (
        db.session.query(ChatbotQuery.message, func.count())
        .filter(ChatbotQuery.matched_faq_id.is_(None), ChatbotQuery.message != "")
        .group_by(ChatbotQuery.message)
        .order_by(func.count().desc())
        .limit(8)
        .all()
    )
    return [{"message": message, "count": count} for message, count in rows]


def _picked_fandom(category):
    raw = request.form.get("fandom_id", "").strip()
    if not raw:
        return None, None
    if not raw.isdigit():
        return None, "Choose a fandom from the list."
    fan = db.session.get(Fandom, int(raw))
    if fan is None or not fan.is_active or (category and fan.category_id != category.category_id):
        return None, "Choose an active fandom in the same category."
    return fan, None


@bp.route("/admin/fandoms", methods=["POST"])
def admin_fandom_create():
    user, bounce = _require_admin()
    if bounce:
        return bounce
    name, error = _clean_name(request.form.get("name"), 2, 120, "Fandom name")
    description, desc_error = _optional_text(request.form.get("description"), 500, "Description")
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0))
    if error or desc_error:
        return _desk_redirect("fandoms", error or desc_error)
    if category is None:
        return _desk_redirect("fandoms", "Choose a category.")
    clash = Fandom.query.filter(func.lower(Fandom.name) == name.lower(), Fandom.category_id == category.category_id).first()
    if clash:
        return _desk_redirect("fandoms", "That fandom already exists in this category.")
    row = Fandom(category_id=category.category_id, name=name, slug=_named_slug(Fandom, name), description=description, is_active=True)
    db.session.add(row)
    _admin_log(user, "fandom.create", name)
    db.session.commit()
    return _desk_redirect("fandoms")


@bp.route("/admin/fandoms/<int:fandom_id>", methods=["POST"])
def admin_fandom_update(fandom_id):
    user, bounce = _require_admin()
    if bounce:
        return bounce
    row = db.session.get(Fandom, fandom_id)
    if row is None:
        return _desk_redirect("fandoms", "That fandom no longer exists.")
    if request.form.get("action") == "hide":
        row.is_active = False
        _admin_log(user, "fandom.hide", row.name)
        db.session.commit()
        return _desk_redirect("fandoms")
    if request.form.get("action") == "show":
        row.is_active = True
        _admin_log(user, "fandom.show", row.name)
        db.session.commit()
        return _desk_redirect("fandoms")
    name, error = _clean_name(request.form.get("name"), 2, 120, "Fandom name")
    description, desc_error = _optional_text(request.form.get("description"), 500, "Description")
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0))
    if error or desc_error:
        return _desk_redirect("fandoms", error or desc_error, fandom_id)
    if category is None:
        return _desk_redirect("fandoms", "Choose a category.", fandom_id)
    clash = Fandom.query.filter(func.lower(Fandom.name) == name.lower(), Fandom.category_id == category.category_id, Fandom.fandom_id != row.fandom_id).first()
    if clash:
        return _desk_redirect("fandoms", "That fandom already exists in this category.", fandom_id)
    row.name = name
    row.category_id = category.category_id
    row.description = description
    _admin_log(user, "fandom.edit", name)
    db.session.commit()
    return _desk_redirect("fandoms")


@bp.route("/admin/fandoms/<int:fandom_id>/delete", methods=["POST"])
def admin_fandom_delete(fandom_id):
    user, bounce = _require_admin()
    if bounce:
        return bounce
    row = db.session.get(Fandom, fandom_id)
    if row is None:
        return _desk_redirect("fandoms", "That fandom no longer exists.")
    if _fandom_in_use(fandom_id):
        row.is_active = False
        _admin_log(user, "fandom.hide", row.name)
        db.session.commit()
        return _desk_redirect("fandoms", "This fandom still has titles, so it was hidden instead of deleted.")
    name = row.name
    db.session.delete(row)
    _admin_log(user, "fandom.delete", name)
    db.session.commit()
    return _desk_redirect("fandoms")


@bp.route("/admin/characters", methods=["POST"])
def admin_character_create():
    user, bounce = _require_admin()
    if bounce:
        return bounce
    name, error = _clean_name(request.form.get("name"), 2, 150, "Character name")
    alias, alias_error = _optional_text(request.form.get("alias"), 150, "Alias")
    bio, bio_error = _optional_text(request.form.get("bio"), 2000, "Bio")
    image, image_error = _optional_url(request.form.get("image_url"), "Image link")
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0))
    if any((error, alias_error, bio_error, image_error)):
        return _desk_redirect("characters", error or alias_error or bio_error or image_error)
    if category is None:
        return _desk_redirect("characters", "Choose a category.")
    fan, fan_error = _picked_fandom(category)
    if fan_error:
        return _desk_redirect("characters", fan_error)
    row = CharacterProfile(category_id=category.category_id, fandom_id=fan.fandom_id if fan else None, name=name, alias=alias, bio=bio, image_url=image)
    db.session.add(row)
    _admin_log(user, "character.create", name)
    db.session.commit()
    return _desk_redirect("characters")


@bp.route("/admin/characters/<int:character_id>", methods=["POST"])
def admin_character_update(character_id):
    user, bounce = _require_admin()
    if bounce:
        return bounce
    row = db.session.get(CharacterProfile, character_id)
    if row is None:
        return _desk_redirect("characters", "That character no longer exists.")
    if request.form.get("action") == "delete":
        name = row.name
        db.session.delete(row)
        _admin_log(user, "character.delete", name)
        db.session.commit()
        return _desk_redirect("characters")
    name, error = _clean_name(request.form.get("name"), 2, 150, "Character name")
    alias, alias_error = _optional_text(request.form.get("alias"), 150, "Alias")
    bio, bio_error = _optional_text(request.form.get("bio"), 2000, "Bio")
    image, image_error = _optional_url(request.form.get("image_url"), "Image link")
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0))
    if any((error, alias_error, bio_error, image_error)):
        return _desk_redirect("characters", error or alias_error or bio_error or image_error, character_id)
    if category is None:
        return _desk_redirect("characters", "Choose a category.", character_id)
    fan, fan_error = _picked_fandom(category)
    if fan_error:
        return _desk_redirect("characters", fan_error, character_id)
    row.name = name
    row.alias = alias
    row.bio = bio
    row.image_url = image
    row.category_id = category.category_id
    row.fandom_id = fan.fandom_id if fan else None
    _admin_log(user, "character.edit", name)
    db.session.commit()
    return _desk_redirect("characters")


def _merch_tags(item):
    MerchandiseTag.query.filter_by(item_id=item.item_id).delete()
    for raw in request.form.getlist("tags"):
        if raw.isdigit():
            tag = db.session.get(Tag, int(raw))
            if tag:
                db.session.add(MerchandiseTag(item_id=item.item_id, tag_id=tag.tag_id))


@bp.route("/admin/merchandise", methods=["POST"])
def admin_merch_create():
    user, bounce = _require_admin()
    if bounce:
        return bounce
    name, error = _clean_name(request.form.get("name"), 2, 200, "Merchandise name")
    description, desc_error = _optional_text(request.form.get("description"), 2000, "Description")
    image, image_error = _optional_url(request.form.get("image_url"), "Image link")
    reference, ref_error = _optional_url(request.form.get("reference_url"), "Reference link")
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0))
    release, release_error = _optional_date(request.form.get("release_date"))
    if any((error, desc_error, image_error, ref_error, release_error)):
        return _desk_redirect("merchandise", error or desc_error or image_error or ref_error or release_error)
    if category is None:
        return _desk_redirect("merchandise", "Choose a category.")
    fan, fan_error = _picked_fandom(category)
    if fan_error:
        return _desk_redirect("merchandise", fan_error)
    row = MerchandiseItem(
        category_id=category.category_id,
        fandom_id=fan.fandom_id if fan else None,
        name=name,
        description=description,
        image_url=image,
        reference_url=reference,
        release_date=release,
        is_upcoming=request.form.get("upcoming") == "yes",
    )
    db.session.add(row)
    db.session.flush()
    _merch_tags(row)
    _admin_log(user, "merch.create", name)
    db.session.commit()
    return _desk_redirect("merchandise")


@bp.route("/admin/merchandise/<int:item_id>", methods=["POST"])
def admin_merch_update(item_id):
    user, bounce = _require_admin()
    if bounce:
        return bounce
    row = db.session.get(MerchandiseItem, item_id)
    if row is None:
        return _desk_redirect("merchandise", "That item no longer exists.")
    if request.form.get("action") == "delete":
        name = row.name
        db.session.delete(row)
        _admin_log(user, "merch.delete", name)
        db.session.commit()
        return _desk_redirect("merchandise")
    name, error = _clean_name(request.form.get("name"), 2, 200, "Merchandise name")
    description, desc_error = _optional_text(request.form.get("description"), 2000, "Description")
    image, image_error = _optional_url(request.form.get("image_url"), "Image link")
    reference, ref_error = _optional_url(request.form.get("reference_url"), "Reference link")
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0))
    release, release_error = _optional_date(request.form.get("release_date"))
    if any((error, desc_error, image_error, ref_error, release_error)):
        return _desk_redirect("merchandise", error or desc_error or image_error or ref_error or release_error, item_id)
    if category is None:
        return _desk_redirect("merchandise", "Choose a category.", item_id)
    fan, fan_error = _picked_fandom(category)
    if fan_error:
        return _desk_redirect("merchandise", fan_error, item_id)
    row.name = name
    row.description = description
    row.image_url = image
    row.reference_url = reference
    row.category_id = category.category_id
    row.fandom_id = fan.fandom_id if fan else None
    row.release_date = release
    row.is_upcoming = request.form.get("upcoming") == "yes"
    _merch_tags(row)
    _admin_log(user, "merch.edit", name)
    db.session.commit()
    return _desk_redirect("merchandise")


def _optional_date(value):
    text = (value or "").strip()
    if not text:
        return None, None
    try:
        return date.fromisoformat(text), None
    except ValueError:
        return None, "Release date must look like 2026-09-25."


def _required_when(value):
    text = (value or "").strip()
    if not text:
        return None, "Start time is required."
    try:
        return datetime.fromisoformat(text), None
    except ValueError:
        return None, "Start time must be a valid date and time."


def _optional_when(value):
    text = (value or "").strip()
    if not text:
        return None, None
    try:
        return datetime.fromisoformat(text), None
    except ValueError:
        return None, "End time must be a valid date and time."


def _coord(value, low, high, label):
    text = (value or "").strip()
    if not text:
        return None, None
    try:
        number = float(text)
    except ValueError:
        return None, f"{label} must be a number."
    if number < low or number > high:
        return None, f"{label} must be between {low} and {high}."
    return number, None


EVENT_TYPES = ("convention", "concert", "meetup", "festival", "expo", "other")


@bp.route("/admin/events", methods=["POST"])
def admin_event_create():
    user, bounce = _require_admin()
    if bounce:
        return bounce
    title, error = _clean_name(request.form.get("title"), 2, 200, "Event title")
    description, desc_error = _optional_text(request.form.get("description"), 2000, "Description")
    city, city_error = _clean_name(request.form.get("city"), 2, 100, "City")
    start, start_error = _required_when(request.form.get("start_at"))
    end, end_error = _optional_when(request.form.get("end_at"))
    ticket, ticket_error = _optional_url(request.form.get("ticket_url"), "Ticket link")
    lat, lat_error = _coord(request.form.get("latitude"), -90, 90, "Latitude")
    lng, lng_error = _coord(request.form.get("longitude"), -180, 180, "Longitude")
    kind = request.form.get("event_type", "other")
    if kind not in EVENT_TYPES:
        kind = "other"
    problems = [error, desc_error, city_error, start_error, end_error, ticket_error, lat_error, lng_error]
    if any(problems):
        return _desk_redirect("events", next(item for item in problems if item))
    if end and start and end < start:
        return _desk_redirect("events", "End time must be after the start time.")
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0)) if request.form.get("category_id") else None
    fan, fan_error = _picked_fandom(category)
    if fan_error:
        return _desk_redirect("events", fan_error)
    row = Event(
        category_id=category.category_id if category else None,
        fandom_id=fan.fandom_id if fan else None,
        title=title,
        description=description,
        event_type=kind,
        venue=(request.form.get("venue") or "").strip()[:255] or None,
        address=(request.form.get("address") or "").strip()[:255] or None,
        city=city,
        country=(request.form.get("country") or "").strip()[:100] or None,
        latitude=lat,
        longitude=lng,
        start_at=start,
        end_at=end,
        ticket_url=ticket,
        created_by=user.user_id,
    )
    db.session.add(row)
    _admin_log(user, "event.create", title)
    db.session.commit()
    return _desk_redirect("events")


@bp.route("/admin/events/<int:event_id>", methods=["POST"])
def admin_event_update(event_id):
    user, bounce = _require_admin()
    if bounce:
        return bounce
    row = db.session.get(Event, event_id)
    if row is None:
        return _desk_redirect("events", "That event no longer exists.")
    if request.form.get("action") == "delete":
        title = row.title
        db.session.delete(row)
        _admin_log(user, "event.delete", title)
        db.session.commit()
        return _desk_redirect("events")
    title, error = _clean_name(request.form.get("title"), 2, 200, "Event title")
    description, desc_error = _optional_text(request.form.get("description"), 2000, "Description")
    city, city_error = _clean_name(request.form.get("city"), 2, 100, "City")
    start, start_error = _required_when(request.form.get("start_at"))
    end, end_error = _optional_when(request.form.get("end_at"))
    ticket, ticket_error = _optional_url(request.form.get("ticket_url"), "Ticket link")
    lat, lat_error = _coord(request.form.get("latitude"), -90, 90, "Latitude")
    lng, lng_error = _coord(request.form.get("longitude"), -180, 180, "Longitude")
    kind = request.form.get("event_type", "other")
    if kind not in EVENT_TYPES:
        kind = "other"
    problems = [error, desc_error, city_error, start_error, end_error, ticket_error, lat_error, lng_error]
    if any(problems):
        return _desk_redirect("events", next(item for item in problems if item), event_id)
    if end and start and end < start:
        return _desk_redirect("events", "End time must be after the start time.", event_id)
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0)) if request.form.get("category_id") else None
    fan, fan_error = _picked_fandom(category)
    if fan_error:
        return _desk_redirect("events", fan_error, event_id)
    row.title = title
    row.description = description
    row.city = city
    row.event_type = kind
    row.venue = (request.form.get("venue") or "").strip()[:255] or None
    row.address = (request.form.get("address") or "").strip()[:255] or None
    row.country = (request.form.get("country") or "").strip()[:100] or None
    row.latitude = lat
    row.longitude = lng
    row.start_at = start
    row.end_at = end
    row.ticket_url = ticket
    row.category_id = category.category_id if category else None
    row.fandom_id = fan.fandom_id if fan else None
    _admin_log(user, "event.edit", title)
    db.session.commit()
    return _desk_redirect("events")


@bp.route("/admin/tags", methods=["POST"])
def admin_tag_create():
    user, bounce = _require_admin()
    if bounce:
        return bounce
    name, error = _clean_name(request.form.get("name"), 2, 60, "Tag name")
    if error:
        return _desk_redirect("tags", error)
    if Tag.query.filter(func.lower(Tag.name) == name.lower()).first():
        return _desk_redirect("tags", "That tag already exists.")
    db.session.add(Tag(name=name))
    _admin_log(user, "tag.create", name)
    db.session.commit()
    return _desk_redirect("tags")


@bp.route("/admin/tags/<int:tag_id>", methods=["POST"])
def admin_tag_update(tag_id):
    user, bounce = _require_admin()
    if bounce:
        return bounce
    row = db.session.get(Tag, tag_id)
    if row is None:
        return _desk_redirect("tags", "That tag no longer exists.")
    if request.form.get("action") == "delete":
        used = MerchandiseTag.query.filter_by(tag_id=tag_id).first() or db.session.query(ContentTag).filter_by(tag_id=tag_id).first()
        if used:
            return _desk_redirect("tags", "This tag is still on a title or merchandise item.")
        name = row.name
        db.session.delete(row)
        _admin_log(user, "tag.delete", name)
        db.session.commit()
        return _desk_redirect("tags")
    name, error = _clean_name(request.form.get("name"), 2, 60, "Tag name")
    if error:
        return _desk_redirect("tags", error, tag_id)
    clash = Tag.query.filter(func.lower(Tag.name) == name.lower(), Tag.tag_id != row.tag_id).first()
    if clash:
        return _desk_redirect("tags", "That tag already exists.", tag_id)
    row.name = name
    _admin_log(user, "tag.edit", name)
    db.session.commit()
    return _desk_redirect("tags")


@bp.route("/admin/faqs", methods=["POST"])
def admin_faq_create():
    user, bounce = _require_admin()
    if bounce:
        return bounce
    question, q_error = _optional_text(request.form.get("question"), 500, "Question")
    answer, a_error = _optional_text(request.form.get("answer"), 2000, "Answer")
    keywords, k_error = _optional_text(request.form.get("keywords"), 500, "Keywords")
    if not question:
        q_error = q_error or "Question is required."
    if not answer:
        a_error = a_error or "Answer is required."
    if q_error or a_error or k_error:
        return _desk_redirect("faqs", q_error or a_error or k_error)
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0)) if request.form.get("category_id") else None
    row = ChatbotFaq(
        category_id=category.category_id if category else None,
        question=question,
        answer=answer,
        keywords=keywords,
        is_active=request.form.get("active") == "yes",
        created_by=user.user_id,
    )
    db.session.add(row)
    _admin_log(user, "faq.create", question[:80])
    db.session.commit()
    return _desk_redirect("faqs")


@bp.route("/admin/faqs/<int:faq_id>", methods=["POST"])
def admin_faq_update(faq_id):
    user, bounce = _require_admin()
    if bounce:
        return bounce
    row = db.session.get(ChatbotFaq, faq_id)
    if row is None:
        return _desk_redirect("faqs", "That FAQ no longer exists.")
    if request.form.get("action") == "delete":
        db.session.delete(row)
        _admin_log(user, "faq.delete", row.question[:80])
        db.session.commit()
        return _desk_redirect("faqs")
    question, q_error = _optional_text(request.form.get("question"), 500, "Question")
    answer, a_error = _optional_text(request.form.get("answer"), 2000, "Answer")
    keywords, k_error = _optional_text(request.form.get("keywords"), 500, "Keywords")
    if not question:
        q_error = q_error or "Question is required."
    if not answer:
        a_error = a_error or "Answer is required."
    if q_error or a_error or k_error:
        return _desk_redirect("faqs", q_error or a_error or k_error, faq_id)
    category = db.session.get(Category, int(request.form.get("category_id", "0") or 0)) if request.form.get("category_id") else None
    row.question = question
    row.answer = answer
    row.keywords = keywords
    row.category_id = category.category_id if category else None
    row.is_active = request.form.get("active") == "yes"
    _admin_log(user, "faq.edit", question[:80])
    db.session.commit()
    return _desk_redirect("faqs")


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
