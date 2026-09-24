import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    if hashed.startswith("$2"):
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    try:
        from werkzeug.security import check_password_hash

        return check_password_hash(hashed, plain)
    except Exception:
        return False


def password_is_strong(plain: str) -> bool:
    return bool(PASSWORD_PATTERN.match(plain))


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_raw_token() -> str:
    return secrets.token_urlsafe(32)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_access_token(user_id: int, role: str, session_version: int = 1) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "sv": int(session_version or 1),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
