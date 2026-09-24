from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class CategoryUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=60)
    description: str | None = None
    cover_url: str | None = None


class FandomIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=140)
    description: str | None = None
    cover_url: str | None = None
    is_active: bool | None = True


class FandomUpdateIn(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = None
    cover_url: str | None = None
    is_active: bool | None = None


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class ContentIn(BaseModel):
    category_id: int
    fandom_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    slug: str | None = None
    type: str = Field(min_length=1, max_length=20)
    summary: str | None = None
    description: str | None = None
    body: str | None = None
    media_url: str | None = None
    embed_url: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    license_url: str | None = None
    rights_confirmed: bool = False
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    release_date: date | None = None
    is_featured: bool = False
    status: str = "published"
    genre_ids: list[int] = []
    tag_ids: list[int] = []
    images: list[dict] = []
    timeline: list[dict] = []


class CharacterIn(BaseModel):
    category_id: int
    fandom_id: int | None = None
    name: str = Field(min_length=1, max_length=150)
    alias: str | None = None
    bio: str | None = None
    image_url: str | None = None


class MerchandiseIn(BaseModel):
    category_id: int
    fandom_id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    image_url: str | None = None
    reference_url: str | None = None
    release_date: date | None = None
    is_upcoming: bool = False
    tag_ids: list[int] = []
    images: list[dict] = []


class EventIn(BaseModel):
    category_id: int | None = None
    fandom_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    event_type: str = "other"
    venue: str | None = None
    address: str | None = None
    city: str = Field(min_length=1, max_length=100)
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    start_at: datetime
    end_at: datetime | None = None
    ticket_url: str | None = None
    cover_url: str | None = None


class BookmarkIn(BaseModel):
    content_id: int | None = None
    character_id: int | None = None
    merchandise_id: int | None = None
    event_id: int | None = None
    note: str | None = None


class BookmarkNoteIn(BaseModel):
    note: str | None = None


class RatingIn(BaseModel):
    score: int = Field(ge=1, le=5)


class FavoritesIn(BaseModel):
    category_ids: list[int] | None = None
    fandom_ids: list[int] | None = None


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    bio: str | None = None
    avatar_url: str | None = None
    theme: str | None = None
    font_size: str | None = None


class DashboardLayoutIn(BaseModel):
    widgets: list[dict]


class SubmissionIn(BaseModel):
    category_id: int
    fandom_id: int | None = None
    content_type: str = "article"
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    media_url: str | None = None
    source_url: str | None = None
    cover_image_url: str | None = None
    rights_confirmed: bool


class ReviewIn(BaseModel):
    decision: str
    reject_reason: str | None = None
    category_id: int | None = None
    tag_ids: list[int] = []


class FeedbackIn(BaseModel):
    type: str
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)
    contact_email: EmailStr | None = None
    page_url: str | None = None
    reproduction_steps: str | None = None
    browser_info: str | None = None


class FeedbackUpdateIn(BaseModel):
    status: str | None = None
    admin_response: str | None = None


class UserAdminUpdateIn(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class FaqIn(BaseModel):
    category_id: int | None = None
    question: str
    answer: str
    keywords: str | None = None
    is_active: bool = True


class ChatMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_token: str | None = None


class OnboardingIn(BaseModel):
    session_token: str | None = None
    action: str = "next"
    category_ids: list[int] = []

