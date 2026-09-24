import jwt
from flask import request

from app.database import get_db
from app.errors import AuthError
from app.models import User
from app.security import decode_access_token


def get_current_user() -> User:
    header = request.headers.get("Authorization", "")
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError(401, "missing_token", "Sign in to continue.")
    try:
        payload = decode_access_token(parts[1])
        if payload.get("type") != "access":
            raise ValueError("wrong type")
        user_id = int(payload["sub"])
        token_sv = int(payload.get("sv", 1))
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise AuthError(401, "session_expired", "Your session expired. Sign in again.")
    user = get_db().get(User, user_id)
    if user is None:
        raise AuthError(401, "session_expired", "Your session expired. Sign in again.")
    if not user.is_active:
        raise AuthError(403, "account_locked", "This account is locked.")
    if int(user.session_version or 1) != token_sv:
        raise AuthError(401, "session_expired", "Your session expired. Sign in again.")
    return user


def get_optional_user():
    header = request.headers.get("Authorization", "")
    if not header:
        return None
    return get_current_user()


def get_admin_user() -> User:
    user = get_current_user()
    if user.role != "admin":
        raise AuthError(403, "not_admin", "Administrator access is required.")
    return user
