from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.db_sp import (
    sp_create_user_token,
    sp_get_user_for_login,
    sp_login_success,
    sp_register_user,
    sp_reset_password,
    sp_verify_email,
)
from app.emailer import send_reset_email, send_verify_email
from app.errors import AuthError
from app.models import User, UserSession
from app.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_raw_token,
    password_is_strong,
    utcnow,
    verify_password,
)

GENERIC_LOGIN_FAIL = "Email or password is not right."
GENERIC_RESET_SENT = "If that email exists, a link has been sent."


def _err(code: int, error: str, message: str) -> AuthError:
    return AuthError(code, error, message)


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def issue_tokens(db: Session, user: User, mark_login: bool = False) -> dict:
    if mark_login:
        user = sp_login_success(db, user)
    raw_refresh = new_raw_token()
    session = UserSession(
        user_id=user.user_id,
        refresh_token_hash=hash_token(raw_refresh),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    return {
        "access_token": create_access_token(user.user_id, user.role, user.session_version),
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in_minutes": settings.access_token_minutes,
    }


def create_purpose_token(db: Session, user: User, purpose: str, ttl: timedelta) -> str:
    raw = new_raw_token()
    minutes = max(1, int(ttl.total_seconds() // 60))
    sp_create_user_token(db, user, purpose, hash_token(raw), minutes)
    return raw


def _revoke_user_sessions(db: Session, user: User) -> None:
    user.session_version = (user.session_version or 1) + 1
    now = utcnow()
    for sess in db.query(UserSession).filter(UserSession.user_id == user.user_id, UserSession.revoked_at.is_(None)):
        sess.revoked_at = now
    db.commit()


def register_user(db: Session, name: str, email: str, password: str, password_confirm: str) -> tuple[User, str]:
    if password != password_confirm:
        raise _err(400, "password_mismatch", "The two passwords do not match.")
    if not password_is_strong(password):
        raise _err(400, "weak_password", "Use at least 8 characters, with a letter and a number.")
    email_n = email.lower().strip()
    if find_user_by_email(db, email_n):
        raise _err(409, "email_exists", "That email is already registered. Sign in or reset the password.")
    user = sp_register_user(db, name.strip(), email_n, hash_password(password))
    raw = create_purpose_token(db, user, "email_verify", timedelta(hours=settings.email_verify_hours))
    send_verify_email(user.email, raw)
    return user, raw


def resend_verification(db: Session, email: str) -> str | None:
    user = find_user_by_email(db, email)
    if user is None or user.email_verified_at is not None:
        return None
    raw = create_purpose_token(db, user, "email_verify", timedelta(hours=settings.email_verify_hours))
    send_verify_email(user.email, raw)
    return raw


def verify_email(db: Session, raw_token: str) -> User:
    if not raw_token:
        raise _err(400, "invalid_token", "That link is not valid.")
    return sp_verify_email(db, hash_token(raw_token))


def login(db: Session, email: str, password: str, require_admin: bool = False) -> dict:
    user = sp_get_user_for_login(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise _err(401, "invalid_credentials", GENERIC_LOGIN_FAIL)
    if not user.is_active:
        raise _err(403, "account_locked", "This account is locked.")
    if user.email_verified_at is None:
        raise _err(
            403,
            "email_unverified",
            "Email is not verified. Open the link in your inbox, or request a new one.",
        )
    if require_admin and user.role != "admin":
        raise _err(403, "not_admin", "This account is not an administrator.")
    return issue_tokens(db, user, mark_login=True)


def logout(db: Session, refresh_token: str) -> None:
    row = (
        db.query(UserSession)
        .filter(UserSession.refresh_token_hash == hash_token(refresh_token))
        .first()
    )
    if row and row.revoked_at is None:
        row.revoked_at = utcnow()
        db.commit()


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    row = (
        db.query(UserSession)
        .filter(UserSession.refresh_token_hash == hash_token(refresh_token))
        .first()
    )
    if row is None or row.revoked_at is not None or row.expires_at < utcnow():
        raise _err(401, "invalid_refresh", "Your session expired. Sign in again.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise _err(403, "account_locked", "This account is locked.")
    row.revoked_at = utcnow()
    db.commit()
    return issue_tokens(db, user, mark_login=False)


def request_password_reset(db: Session, email: str) -> str | None:
    user = find_user_by_email(db, email)
    if user is None:
        return None
    raw = create_purpose_token(
        db, user, "password_reset", timedelta(minutes=settings.password_reset_minutes)
    )
    send_reset_email(user.email, raw)
    return raw


def reset_password(db: Session, raw_token: str, password: str, password_confirm: str) -> None:
    if password != password_confirm:
        raise _err(400, "password_mismatch", "The two passwords do not match.")
    if not password_is_strong(password):
        raise _err(400, "weak_password", "Use at least 8 characters, with a letter and a number.")
    user = sp_reset_password(db, hash_token(raw_token), hash_password(password))
    _revoke_user_sessions(db, user)


def seed_admin(db: Session) -> None:
    email = settings.seed_admin_email.lower()
    if find_user_by_email(db, email):
        return
    admin = User(
        name=settings.seed_admin_name,
        email=email,
        password_hash=hash_password(settings.seed_admin_password),
        role="admin",
        is_active=True,
        session_version=1,
        email_verified_at=utcnow(),
    )
    db.add(admin)
    db.commit()
