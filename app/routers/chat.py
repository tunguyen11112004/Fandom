import uuid

from flask import Blueprint

from app.database import get_db
from app.deps import get_admin_user, get_current_user, get_optional_user
from app.errors import AuthError
from app.http_json import ok, parse_body
from app.models import Category, ChatbotFaq, ChatbotQuery, ChatSession, Content, UserCategory
from app.schemas_extra import ChatMessageIn, FaqIn, OnboardingIn
from app.serialize import log_activity, row_dict
from app.security import like_contains, utcnow

bp = Blueprint("chat", __name__)
bp.strict_slashes = False
FALLBACK = "No matching FAQ yet. Search the catalog or send feedback (POST /feedback)."
ONBOARD_STEPS = [
    "Pick the categories you care about.",
    "Open a category to see articles, characters, and merchandise.",
    "Use search and filters to narrow the results.",
    "Sign in to bookmark titles you care about.",
    "Browse events near you or by city.",
]


def _match_faq(db, message: str) -> ChatbotFaq | None:
    text = (message or "").lower()
    faqs = db.query(ChatbotFaq).filter(ChatbotFaq.is_active.is_(True)).all()
    best = None
    best_score = 0
    for faq in faqs:
        hay = f"{faq.question} {faq.keywords or ''}".lower()
        score = sum(1 for w in text.split() if len(w) > 2 and w in hay)
        if score > best_score:
            best, best_score = faq, score
    return best if best_score > 0 else None


@bp.post("/chat/sessions")
def start_session():
    user = get_optional_user()
    db = get_db()
    row = ChatSession(user_id=user.user_id if user else None, session_token=str(uuid.uuid4()), current_step=0)
    db.add(row)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.post("/chat/messages")
def send_message():
    user = get_optional_user()
    db = get_db()
    body = parse_body(ChatMessageIn)
    session = None
    if body.session_token:
        session = db.query(ChatSession).filter(ChatSession.session_token == body.session_token).first()
    if session is None:
        session = ChatSession(user_id=user.user_id if user else None, session_token=str(uuid.uuid4()), current_step=0)
        db.add(session)
        db.flush()
    if user and session.user_id is None:
        session.user_id = user.user_id
    faq = _match_faq(db, body.message)
    related = []
    if faq:
        answer = faq.answer
        related = [
            row_dict(c)
            for c in db.query(Content).filter(Content.status == "published").order_by(Content.popularity_score.desc()).limit(3).all()
        ]
    else:
        answer = FALLBACK
        like = like_contains(body.message)
        related = [
            row_dict(c)
            for c in db.query(Content).filter(Content.status == "published", Content.title.ilike(like)).limit(5).all()
        ]
    msg = ChatbotQuery(
        session_id=session.session_id,
        user_id=user.user_id if user else None,
        message=body.message,
        response=answer,
        matched_faq_id=faq.faq_id if faq else None,
    )
    session.last_activity_at = utcnow()
    db.add(msg)
    db.commit()
    return ok(
        data={
            "session_token": session.session_token,
            "matched": faq is not None,
            "faq": row_dict(faq) if faq else None,
            "response": answer,
            "related": related,
            "fallback_actions": None if faq else [{"label": "Search", "path": "/contents"}, {"label": "Send feedback", "path": "/feedback"}],
        }
    )


@bp.get("/chat/sessions/<token>/history")
def history(token: str):
    db = get_db()
    session = db.query(ChatSession).filter(ChatSession.session_token == token).first()
    if session is None:
        raise AuthError(404, "not_found", "Chat session not found.")
    rows = (
        db.query(ChatbotQuery)
        .filter(ChatbotQuery.session_id == session.session_id)
        .order_by(ChatbotQuery.created_at.asc())
        .all()
    )
    return ok(data=[row_dict(r) for r in rows])


@bp.post("/chat/onboarding")
def onboarding():
    user = get_optional_user()
    db = get_db()
    body = parse_body(OnboardingIn)
    session = None
    if body.session_token:
        session = db.query(ChatSession).filter(ChatSession.session_token == body.session_token).first()
    if session is None:
        session = ChatSession(user_id=user.user_id if user else None, session_token=str(uuid.uuid4()), current_step=0)
        db.add(session)
        db.flush()
    if body.action == "skip":
        session.onboarding_completed = True
        session.current_step = len(ONBOARD_STEPS)
    elif body.action == "set_categories" and user and body.category_ids:
        db.query(UserCategory).filter(UserCategory.user_id == user.user_id).delete()
        for cid in set(body.category_ids):
            if db.get(Category, cid):
                db.add(UserCategory(user_id=user.user_id, category_id=cid))
        session.current_step = max(session.current_step, 1)
    else:
        session.current_step = min(int(session.current_step or 0) + 1, len(ONBOARD_STEPS))
        if session.current_step >= len(ONBOARD_STEPS):
            session.onboarding_completed = True
    session.last_activity_at = utcnow()
    suggestions = []
    if user:
        ids = [c.category_id for c in db.query(UserCategory).filter(UserCategory.user_id == user.user_id).all()]
        if ids:
            suggestions = db.query(Content).filter(Content.status == "published", Content.category_id.in_(ids)).limit(5).all()
    idx = min(int(session.current_step or 0), len(ONBOARD_STEPS) - 1)
    prompt = "Onboarding is done. You can ask the FAQ next." if session.onboarding_completed else ONBOARD_STEPS[idx]
    db.commit()
    return ok(
        data={
            "session_token": session.session_token,
            "current_step": session.current_step,
            "onboarding_completed": session.onboarding_completed,
            "prompt": prompt,
            "suggestions": [row_dict(c) for c in suggestions],
        }
    )


@bp.get("/admin/faqs")
def admin_list_faqs():
    get_admin_user()
    rows = get_db().query(ChatbotFaq).order_by(ChatbotFaq.faq_id).all()
    return ok(data=[row_dict(r) for r in rows])


@bp.post("/admin/faqs")
def admin_create_faq():
    admin = get_admin_user()
    db = get_db()
    body = parse_body(FaqIn)
    row = ChatbotFaq(**body.model_dump(), created_by=admin.user_id)
    db.add(row)
    db.flush()
    log_activity(db, admin.user_id, "faq_create", "faq", row.faq_id)
    db.commit()
    return ok(data=row_dict(row), status=201)


@bp.put("/admin/faqs/<int:faq_id>")
def admin_update_faq(faq_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(ChatbotFaq, faq_id)
    if row is None:
        raise AuthError(404, "not_found", "FAQ not found.")
    body = parse_body(FaqIn)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    log_activity(db, admin.user_id, "faq_update", "faq", faq_id)
    db.commit()
    return ok(data=row_dict(row))


@bp.delete("/admin/faqs/<int:faq_id>")
def admin_delete_faq(faq_id: int):
    admin = get_admin_user()
    db = get_db()
    row = db.get(ChatbotFaq, faq_id)
    if row is None:
        raise AuthError(404, "not_found", "FAQ not found.")
    log_activity(db, admin.user_id, "faq_delete", "faq", faq_id)
    db.delete(row)
    db.commit()
    return ok(message="FAQ deleted.")
