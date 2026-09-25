from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="light")
    font_size: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    tokens: Mapped[list["UserToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="user")

    @property
    def id(self):
        return self.user_id

    @property
    def is_member(self):
        return self.role == "user"

    @property
    def locked(self):
        return not self.is_active

    @locked.setter
    def locked(self, value):
        self.is_active = not bool(value)

    @property
    def verified(self):
        return self.email_verified_at is not None

    @verified.setter
    def verified(self, value):
        from app.security import utcnow

        self.email_verified_at = utcnow() if value else None

    @property
    def last_seen(self):
        return self.last_login_at

    @last_seen.setter
    def last_seen(self, value):
        self.last_login_at = value

    @property
    def favorite(self):
        return self.bio or ""

    @favorite.setter
    def favorite(self, value):
        self.bio = (value or "")[:500] or None

    @property
    def avatar_path(self):
        url = self.avatar_url or ""
        return url[8:] if url.startswith("/static/") else url

    @avatar_path.setter
    def avatar_path(self, value):
        self.avatar_url = value


class UserToken(db.Model):
    __tablename__ = "user_tokens"

    token_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    user: Mapped[User] = relationship(back_populates="tokens")


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    user: Mapped[User] = relationship(back_populates="sessions")


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    user: Mapped[User | None] = relationship(back_populates="activity_logs")

    @property
    def id(self):
        return self.log_id

    @property
    def kind(self):
        return self.action

    @property
    def summary(self):
        return self.details or ""

    @property
    def detail(self):
        return self.details or ""

    @property
    def href(self):
        return ""


class Category(db.Model):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contents: Mapped[list["Content"]] = relationship(back_populates="category")

    @property
    def id(self):
        return self.category_id

    @property
    def image_path(self):
        from app.media import category_file

        return category_file(self.slug)

    @property
    def image_credit(self):
        from app.media import category_credit

        return category_credit(self.slug)


class Fandom(db.Model):
    __tablename__ = "fandoms"

    fandom_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class UserCategory(db.Model):
    __tablename__ = "user_categories"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="CASCADE"), primary_key=True)


class UserFandom(db.Model):
    __tablename__ = "user_fandoms"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    fandom_id: Mapped[int] = mapped_column(ForeignKey("fandoms.fandom_id", ondelete="CASCADE"), primary_key=True)


class Genre(db.Model):
    __tablename__ = "genres"
    genre_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)


class Tag(db.Model):
    __tablename__ = "tags"
    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)


class Content(db.Model):
    __tablename__ = "contents"

    content_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    fandom_id: Mapped[int | None] = mapped_column(ForeignKey("fandoms.fandom_id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embed_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    popularity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    images: Mapped[list["ContentImage"]] = relationship(cascade="all, delete-orphan")
    timeline: Mapped[list["ContentTimelineEntry"]] = relationship(cascade="all, delete-orphan")
    category: Mapped["Category"] = relationship(back_populates="contents")
    genre_links: Mapped[list["ContentGenre"]] = relationship(cascade="all, delete-orphan")

    @property
    def id(self):
        return self.content_id

    @property
    def content_type(self):
        return self.type

    @content_type.setter
    def content_type(self, value):
        allowed = {"article", "video", "audio", "image", "trailer", "explainer"}
        self.type = value if value in allowed else "article"

    @property
    def published(self):
        return self.status == "published"

    @published.setter
    def published(self, value):
        self.status = "published" if value else "archived"

    @property
    def featured(self):
        return self.is_featured

    @featured.setter
    def featured(self, value):
        self.is_featured = bool(value)

    @property
    def release_year(self):
        return self.release_date.year if self.release_date else None

    @release_year.setter
    def release_year(self, value):
        self.release_date = date(int(value), 1, 1)

    @property
    def genre(self):
        names = [link.genre.name for link in self.genre_links if getattr(link, "genre", None)]
        return names[0] if names else ""

    @property
    def image_path(self):
        from app.media import content_file

        return content_file(self.slug) or (self.thumbnail_url.split("/")[-1] if self.thumbnail_url else None)

    @property
    def image_credit(self):
        from app.media import content_credit

        return content_credit(self.slug)

    @property
    def tags(self):
        if not self.content_id:
            return ""
        names = (
            db.session.query(Tag.name)
            .join(ContentTag, ContentTag.tag_id == Tag.tag_id)
            .filter(ContentTag.content_id == self.content_id)
            .order_by(Tag.name.asc())
            .all()
        )
        return ", ".join(name for (name,) in names)

    @tags.setter
    def tags(self, value):
        if not self.content_id:
            return
        names = []
        for part in str(value or "").replace(";", ",").split(","):
            name = " ".join(part.split())[:60]
            if name and name.lower() not in {item.lower() for item in names}:
                names.append(name)
        ContentTag.query.filter_by(content_id=self.content_id).delete()
        for name in names:
            tag = Tag.query.filter(func.lower(Tag.name) == name.lower()).first()
            if tag is None:
                tag = Tag(name=name)
                db.session.add(tag)
                db.session.flush()
            db.session.add(ContentTag(content_id=self.content_id, tag_id=tag.tag_id))


class ContentGenre(db.Model):
    __tablename__ = "content_genres"
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.content_id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.genre_id", ondelete="CASCADE"), primary_key=True)
    genre: Mapped["Genre"] = relationship()


class ContentTag(db.Model):
    __tablename__ = "content_tags"
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.content_id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.tag_id", ondelete="CASCADE"), primary_key=True)


class ContentImage(db.Model):
    __tablename__ = "content_images"
    image_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.content_id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ContentTimelineEntry(db.Model):
    __tablename__ = "content_timeline_entries"
    entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.content_id", ondelete="CASCADE"), nullable=False)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CharacterProfile(db.Model):
    __tablename__ = "character_profiles"
    character_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    fandom_id: Mapped[int | None] = mapped_column(ForeignKey("fandoms.fandom_id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(150), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class MerchandiseItem(db.Model):
    __tablename__ = "merchandise_items"
    item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    fandom_id: Mapped[int | None] = mapped_column(ForeignKey("fandoms.fandom_id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_upcoming: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    images: Mapped[list["MerchandiseImage"]] = relationship(cascade="all, delete-orphan")


class MerchandiseTag(db.Model):
    __tablename__ = "merchandise_tags"
    item_id: Mapped[int] = mapped_column(ForeignKey("merchandise_items.item_id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.tag_id", ondelete="CASCADE"), primary_key=True)


class MerchandiseImage(db.Model):
    __tablename__ = "merchandise_images"
    image_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("merchandise_items.item_id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    bookmark_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[int | None] = mapped_column(ForeignKey("contents.content_id", ondelete="CASCADE"), nullable=True)
    character_id: Mapped[int | None] = mapped_column(ForeignKey("character_profiles.character_id", ondelete="CASCADE"), nullable=True)
    merchandise_id: Mapped[int | None] = mapped_column(ForeignKey("merchandise_items.item_id", ondelete="CASCADE"), nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.event_id", ondelete="CASCADE"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    content: Mapped["Content | None"] = relationship()
    character: Mapped["CharacterProfile | None"] = relationship()
    merchandise: Mapped["MerchandiseItem | None"] = relationship()
    event: Mapped["Event | None"] = relationship()

    @property
    def id(self):
        return self.bookmark_id


class ContentRating(db.Model):
    __tablename__ = "content_ratings"
    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_rating_user_content"),)
    rating_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.content_id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ChatbotFaq(db.Model):
    __tablename__ = "chatbot_faqs"
    faq_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"
    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    session_token: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ChatbotQuery(db.Model):
    __tablename__ = "chatbot_queries"
    query_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_faq_id: Mapped[int | None] = mapped_column(ForeignKey("chatbot_faqs.faq_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class Feedback(db.Model):
    __tablename__ = "feedbacks"
    feedback_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reproduction_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def id(self):
        return self.feedback_id

    @property
    def email(self):
        return self.contact_email or ""

    @property
    def kind(self):
        return self.type

    @property
    def steps(self):
        return self.reproduction_steps or ""

    @property
    def admin_note(self):
        return self.admin_response or ""

    @admin_note.setter
    def admin_note(self, value):
        self.admin_response = value


class Event(db.Model):
    __tablename__ = "events"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True)
    fandom_id: Mapped[int | None] = mapped_column(ForeignKey("fandoms.fandom_id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ticket_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class FanSubmission(db.Model):
    __tablename__ = "fan_submissions"
    submission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    fandom_id: Mapped[int | None] = mapped_column(ForeignKey("fandoms.fandom_id", ondelete="SET NULL"), nullable=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="article")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_content_id: Mapped[int | None] = mapped_column(ForeignKey("contents.content_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    author: Mapped["User"] = relationship(foreign_keys=[user_id])
    category: Mapped["Category"] = relationship()

    @property
    def id(self):
        return self.submission_id

    @property
    def rights_ok(self):
        return self.rights_confirmed

    @rights_ok.setter
    def rights_ok(self, value):
        self.rights_confirmed = bool(value)


class ModerationLog(db.Model):
    __tablename__ = "moderation_logs"
    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("fan_submissions.submission_id", ondelete="CASCADE"), nullable=False)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class Notification(db.Model):
    __tablename__ = "notifications"
    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class UserDashboardWidget(db.Model):
    __tablename__ = "user_dashboard_widgets"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    widget_key: Mapped[str] = mapped_column(String(30), primary_key=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
