from datetime import datetime, timezone

from . import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(200))
    image_credit = db.Column(db.String(240))

    contents = db.relationship(
        "Content", back_populates="category", order_by="Content.title"
    )


class Content(db.Model):
    __tablename__ = "contents"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    content_type = db.Column(db.String(20), nullable=False)
    genre = db.Column(db.String(80), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    release_year = db.Column(db.Integer, nullable=False)
    popularity_score = db.Column(db.Integer, nullable=False, default=0)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    published = db.Column(db.Boolean, nullable=False, default=True)
    featured = db.Column(db.Boolean, nullable=False, default=False)
    tags = db.Column(db.String(200), nullable=False, default="")
    embed_url = db.Column(db.String(300), nullable=False, default="")
    image_path = db.Column(db.String(200))
    image_credit = db.Column(db.String(240))

    category = db.relationship("Category", back_populates="contents")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="member")
    verified = db.Column(db.Boolean, nullable=False, default=False)
    locked = db.Column(db.Boolean, nullable=False, default=False)
    favorite = db.Column(db.String(120), nullable=False, default="")
    interests = db.Column(db.String(240), nullable=False, default="")
    theme = db.Column(db.String(20), nullable=False, default="dark")
    font_size = db.Column(db.String(20), nullable=False, default="medium")
    avatar_path = db.Column(db.String(200), nullable=False, default="")
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class AuthToken(db.Model):
    __tablename__ = "auth_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)
    token = db.Column(db.String(80), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User")


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    __table_args__ = (db.UniqueConstraint("user_id", "content_id", name="uq_bookmark"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id"), nullable=False)
    note = db.Column(db.String(280), nullable=False, default="")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User")
    content = db.relationship("Content")


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(40), nullable=False)
    summary = db.Column(db.String(240), nullable=False)
    href = db.Column(db.String(240), nullable=False, default="")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class FanSubmission(db.Model):
    __tablename__ = "fan_submissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(20), nullable=False, default="article")
    body = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(300), nullable=False, default="")
    rights_ok = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    reject_reason = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    author = db.relationship("User")
    category = db.relationship("Category")


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    email = db.Column(db.String(180), nullable=False, default="")
    kind = db.Column(db.String(20), nullable=False)
    page_url = db.Column(db.String(300), nullable=False, default="")
    steps = db.Column(db.Text, nullable=False, default="")
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new")
    admin_note = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    author = db.relationship("User")


class AdminLog(db.Model):
    __tablename__ = "admin_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    detail = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    admin = db.relationship("User")


class ChatTurn(db.Model):
    __tablename__ = "chat_turns"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
