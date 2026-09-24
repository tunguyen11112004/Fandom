import os
import re
import secrets
from datetime import datetime, timedelta, timezone

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
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import (
    Activity,
    AdminLog,
    AuthToken,
    Bookmark,
    Category,
    ChatTurn,
    Content,
    FanSubmission,
    Feedback,
    User,
)

bp = Blueprint("account", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if user is None or user.locked:
        session.pop("user_id", None)
        return None
    user.last_seen = datetime.now(timezone.utc)
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
    AuthToken.query.filter_by(user_id=user.id, purpose=purpose, used=False).update(
        {"used": True}
    )
    token = AuthToken(
        user_id=user.id,
        purpose=purpose,
        token=secrets.token_urlsafe(24),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    )
    db.session.add(token)
    db.session.commit()
    return token


def _take(token_value, purpose):
    row = AuthToken.query.filter_by(token=token_value, purpose=purpose).first()
    if row is None or row.used or _aware(row.expires_at) < datetime.now(timezone.utc):
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
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
                role="member",
            )
            db.session.add(user)
            db.session.commit()
            token = _issue(user, "verify", 24)
            return redirect(url_for("account.sent", purpose="verify", token=token.token))
    return render_template("auth/register.html", error=error)


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if (
            user is None
            or user.role != "member"
            or not check_password_hash(user.password_hash, password)
        ):
            error = "Email or password is not right."
        elif user.locked:
            error = "This account is locked."
        elif not user.verified:
            error = "Verify your email before signing in."
        else:
            session["user_id"] = user.id
            nxt = request.args.get("next") or url_for("account.dashboard")
            if not nxt.startswith("/"):
                nxt = url_for("account.dashboard")
            return redirect(nxt)
    return render_template("auth/login.html", error=error)


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
            token_value = _issue(user, "reset", 0.5).token
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
    row.used = True
    row.user.verified = True
    db.session.commit()
    return redirect(url_for("account.login"))


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
            row.user.password_hash = generate_password_hash(password, method="pbkdf2:sha256")
            row.used = True
            db.session.commit()
            return redirect(url_for("account.login"))
    return render_template("auth/reset.html", error=error, token=token)


def _member():
    user = current_user()
    if user is None or user.role != "member":
        return None
    return user


def _admin():
    user = current_user()
    if user is None or user.role != "admin":
        return None
    return user


def _log_activity(user, kind, summary, href=""):
    db.session.add(Activity(user_id=user.id, kind=kind, summary=summary, href=href))


def _admin_log(admin, action, detail):
    db.session.add(AdminLog(admin_id=admin.id, action=action, detail=detail[:300]))


def _slugify(title, ignore_id=None):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "title"
    slug = base
    number = 2
    while True:
        taken = Content.query.filter_by(slug=slug).first()
        if taken is None or taken.id == ignore_id:
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
        Bookmark.query.filter_by(user_id=user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    if kind:
        bookmarks = [row for row in bookmarks if row.content and row.content.content_type == kind]
    activity = (
        Activity.query.filter_by(user_id=user.id)
        .order_by(Activity.id.desc())
        .limit(8)
        .all()
    )
    picks = []
    if user.favorite:
        picks = (
            Content.query.filter(
                Content.published.is_(True),
                Content.title.ilike(f"%{user.favorite}%"),
            )
            .order_by(Content.popularity_score.desc())
            .limit(4)
            .all()
        )
    if not picks and user.interests:
        slugs = [part for part in user.interests.split(",") if part]
        if slugs:
            picks = (
                Content.query.join(Category)
                .filter(Content.published.is_(True), Category.slug.in_(slugs))
                .order_by(Content.popularity_score.desc())
                .limit(4)
                .all()
            )
    submissions = (
        FanSubmission.query.filter_by(user_id=user.id)
        .order_by(FanSubmission.id.desc())
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
        categories=Category.query.order_by(Category.id).all(),
    )


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if user is None:
        return redirect(url_for("account.login", next=request.path))
    error = None
    categories = Category.query.order_by(Category.id).all()
    if request.method == "POST":
        user.name = request.form.get("name", user.name).strip() or user.name
        user.favorite = request.form.get("favorite", "").strip()[:120]
        chosen = request.form.getlist("interests")
        allowed = {category.slug for category in categories}
        user.interests = ",".join(slug for slug in chosen if slug in allowed)
        theme = request.form.get("theme", "dark")
        font = request.form.get("font", "medium")
        user.theme = theme if theme in {"dark", "light"} else "dark"
        user.font_size = font if font in {"small", "medium", "large"} else "medium"
        upload = request.files.get("avatar")
        if upload and upload.filename:
            ext = upload.filename.rsplit(".", 1)[-1].lower()
            blob = upload.read()
            if ext not in {"png", "jpg", "jpeg", "webp"} or len(blob) > 1_000_000:
                error = "Use a PNG, JPG, or WEBP under 1 MB. Your other changes were kept."
            else:
                folder = os.path.join(current_app.static_folder, "uploads", "avatars")
                os.makedirs(folder, exist_ok=True)
                filename = f"{user.id}-{secrets.token_hex(4)}.{ext}"
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
        chosen=set(user.interests.split(",")) if user.interests else set(),
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
    row = Bookmark.query.filter_by(user_id=user.id, content_id=item.id).first()
    action = request.form.get("action", "save")
    if action == "remove" and row is not None:
        db.session.delete(row)
        _log_activity(user, "bookmark", f"Removed {item.title}", f"/explore/{item.slug}")
    elif row is None:
        db.session.add(
            Bookmark(
                user_id=user.id,
                content_id=item.id,
                note=request.form.get("note", "").strip()[:280],
            )
        )
        _log_activity(user, "bookmark", f"Bookmarked {item.title}", f"/explore/{item.slug}")
    else:
        row.note = request.form.get("note", "").strip()[:280]
    db.session.commit()
    nxt = request.form.get("next") or url_for("main.content_detail", slug=slug)
    if not nxt.startswith("/"):
        nxt = url_for("account.dashboard")
    return redirect(nxt)


@bp.route("/submissions", methods=["GET", "POST"])
def submissions():
    user = _member()
    if user is None:
        return redirect(url_for("account.login", next=request.path))
    error = None
    categories = Category.query.order_by(Category.id).all()
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
                row = FanSubmission.query.filter_by(id=int(row_id), user_id=user.id).first()
            if row is None:
                row = FanSubmission(user_id=user.id, category_id=category.id)
                db.session.add(row)
            elif row.status not in {"pending", "rejected"}:
                error = "That piece is already published."
            if error is None:
                row.category_id = category.id
                row.title = title[:200]
                row.body = body
                row.content_type = content_type
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
                user_id=user.id if user else None,
                email=user.email if user else email,
                kind=kind,
                page_url=page_url[:300],
                steps=steps,
                message=message,
            )
            db.session.add(row)
            if user and user.role == "member":
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
            or not check_password_hash(user.password_hash, password)
        ):
            error = "Admin sign-in was refused."
        else:
            session["user_id"] = user.id
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
    active_query = User.query.filter(User.role == "member", User.last_seen.isnot(None))
    chat_query = ChatTurn.query
    if since is not None:
        active_query = active_query.filter(User.last_seen >= since)
        chat_query = chat_query.filter(ChatTurn.created_at >= since)
    popular = (
        db.session.query(Category.name, func.count(Content.id))
        .join(Content, Content.category_id == Category.id)
        .group_by(Category.id)
        .order_by(func.count(Content.id).desc())
        .all()
    )
    members = User.query.filter_by(role="member").order_by(User.name).all()
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        members = (
            User.query.filter(User.role == "member")
            .filter(or_(User.name.ilike(like), User.email.ilike(like)))
            .order_by(User.name)
            .all()
        )
    return render_template(
        "auth/admin.html",
        user=user,
        days=days,
        active_users=active_query.count(),
        member_count=User.query.filter_by(role="member").count(),
        chat_count=chat_query.count(),
        popular=popular,
        titles=Content.query.order_by(Content.title).all(),
        categories=Category.query.order_by(Category.id).all(),
        members=members,
        queue=FanSubmission.query.filter_by(status="pending").order_by(FanSubmission.id.asc()).all(),
        feedback_rows=_feedback_rows(),
        logs=AdminLog.query.order_by(AdminLog.id.desc()).limit(12).all(),
        submission_counts=dict(
            db.session.query(FanSubmission.user_id, func.count(FanSubmission.id))
            .group_by(FanSubmission.user_id)
            .all()
        ),
        query=q,
        kinds=request.args.get("kind", ""),
        states=request.args.get("status", ""),
        open_feedback=Feedback.query.filter(Feedback.status != "done").count(),
        title_count=Content.query.count(),
    )


def _feedback_rows():
    query = Feedback.query
    kind = request.args.get("kind", "").strip()
    status = request.args.get("status", "").strip()
    if kind in {"bug", "suggestion", "query"}:
        query = query.filter_by(kind=kind)
    if status in {"new", "reviewing", "done"}:
        query = query.filter_by(status=status)
    return query.order_by(Feedback.id.desc()).all()


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
    if content_type not in {"article", "video", "audio", "profile", "merch", "release"}:
        return "That content type is not on the desk."
    if embed and not embed.startswith(("http://", "https://")):
        return "Embed links need to start with http:// or https://."
    item.category_id = category.id
    item.title = title[:200]
    item.slug = item.slug or _slugify(title)
    if request.form.get("retitle") == "yes":
        item.slug = _slugify(title, item.id)
    item.content_type = content_type
    item.genre = genre[:80]
    item.release_year = int(year)
    item.summary = summary
    item.body = body
    item.embed_url = embed[:300]
    item.tags = tags[:200]
    item.featured = request.form.get("featured") == "yes"
    item.published = request.form.get("published") == "yes"
    score = request.form.get("popularity_score", "50")
    item.popularity_score = int(score) if score.isdigit() else 50
    return None


@bp.route("/admin/content", methods=["POST"])
def admin_content_create():
    user = _admin()
    if user is None:
        return redirect(url_for("account.admin_login"))
    item = Content(slug="", category_id=1, title="", content_type="article", genre="", summary="", body="", release_year=2026)
    error = _content_from_form(item)
    if error:
        return redirect(url_for("account.admin_home", error=error))
    item.slug = _slugify(item.title)
    db.session.add(item)
    _admin_log(user, "content.create", item.title)
    db.session.commit()
    return redirect(url_for("account.admin_home") + "#content")


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
        return redirect(url_for("account.admin_home") + "#content")
    error = _content_from_form(item)
    if error is None:
        _admin_log(user, "content.edit", item.title)
        db.session.commit()
    return redirect(url_for("account.admin_home") + "#content")


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
    return redirect(url_for("account.admin_home") + "#categories")


@bp.route("/admin/users/<int:user_id>", methods=["POST"])
def admin_user(user_id):
    admin = _admin()
    if admin is None:
        return redirect(url_for("account.admin_login"))
    member = db.session.get(User, user_id)
    if member is not None and member.role == "member":
        member.locked = request.form.get("locked") == "yes"
        _admin_log(admin, "user.lock" if member.locked else "user.unlock", member.email)
        db.session.commit()
    return redirect(url_for("account.admin_home") + "#users")


@bp.route("/admin/submissions/<int:submission_id>", methods=["POST"])
def admin_submission(submission_id):
    admin = _admin()
    if admin is None:
        return redirect(url_for("account.admin_login"))
    row = db.session.get(FanSubmission, submission_id)
    if row is None:
        return redirect(url_for("account.admin_home") + "#queue")
    decision = request.form.get("decision")
    if decision == "approve":
        item = Content(
            category_id=row.category_id,
            title=row.title,
            slug=_slugify(row.title),
            content_type=row.content_type if row.content_type in {"article", "video", "profile", "image"} else "article",
            genre=row.category.name,
            summary=row.body[:180],
            body=row.body,
            release_year=datetime.now(timezone.utc).year,
            popularity_score=40,
            embed_url=row.media_url,
            published=True,
            tags="fan",
        )
        db.session.add(item)
        row.status = "approved"
        row.reject_reason = ""
        _admin_log(admin, "submission.approve", row.title)
    elif decision == "reject":
        reason = request.form.get("reason", "").strip() or "Needs a revision."
        row.status = "rejected"
        row.reject_reason = reason[:300]
        _admin_log(admin, "submission.reject", f"{row.title}: {row.reject_reason}")
    db.session.commit()
    return redirect(url_for("account.admin_home") + "#queue")


@bp.route("/admin/feedback/<int:feedback_id>", methods=["POST"])
def admin_feedback(feedback_id):
    admin = _admin()
    if admin is None:
        return redirect(url_for("account.admin_login"))
    row = db.session.get(Feedback, feedback_id)
    if row is None:
        return redirect(url_for("account.admin_home") + "#feedback")
    if request.form.get("action") == "delete":
        _admin_log(admin, "feedback.delete", row.email)
        db.session.delete(row)
    else:
        status = request.form.get("status", row.status)
        if status in {"new", "reviewing", "done"}:
            row.status = status
        row.admin_note = request.form.get("admin_note", "").strip()[:300]
        _admin_log(admin, "feedback.update", f"{row.kind} → {row.status}")
    db.session.commit()
    return redirect(url_for("account.admin_home") + "#feedback")
