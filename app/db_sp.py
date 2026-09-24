from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AuthError
from app.models import ActivityLog, User, UserToken
from app.security import utcnow


def uses_mysql() -> bool:
    return settings.database_url.startswith("mysql")


def _raise_from_sql(exc: Exception) -> None:
    msg = str(exc)
    lowered = msg.lower()
    if "email already registered" in lowered or "duplicate" in lowered:
        raise AuthError(409, "email_exists", "Email đã tồn tại. Hãy đăng nhập hoặc khôi phục mật khẩu.") from exc
    if "invalid name or email" in lowered:
        raise AuthError(400, "invalid_input", "Tên hoặc email không hợp lệ.") from exc
    if "invalid or expired token" in lowered:
        raise AuthError(400, "invalid_token", "Liên kết không hợp lệ hoặc hết hạn.") from exc
    if "user not found or inactive" in lowered:
        raise AuthError(403, "account_locked", "Tài khoản đã bị khóa.") from exc
    raise AuthError(400, "db_error", "Không thực hiện được thao tác dữ liệu.") from exc


def _log(db: Session, user_id: int | None, action: str, entity_type: str | None, entity_id: int | None, details: str | None = None) -> None:
    db.add(
        ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )


def sp_register_user(db: Session, name: str, email: str, password_hash: str) -> User:
    if uses_mysql():
        try:
            db.execute(
                text("CALL sp_register_user(:name, :email, :pw, @p_user_id)"),
                {"name": name, "email": email, "pw": password_hash},
            )
            user_id = db.execute(text("SELECT @p_user_id")).scalar()
            db.commit()
        except (OperationalError, IntegrityError) as exc:
            db.rollback()
            _raise_from_sql(exc)
        user = db.get(User, int(user_id))
        if user is None:
            raise AuthError(500, "db_error", "Không tạo được tài khoản.")
        return user

    user = User(name=name.strip(), email=email.lower().strip(), password_hash=password_hash, role="user")
    db.add(user)
    try:
        db.flush()
        _log(db, user.user_id, "register", "user", user.user_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        _raise_from_sql(exc)
    db.refresh(user)
    return user


def sp_get_user_for_login(db: Session, email: str) -> User | None:
    if uses_mysql():
        row = db.execute(text("CALL sp_get_user_for_login(:email)"), {"email": email}).mappings().first()
        if row is None:
            return None
        return db.get(User, int(row["user_id"]))
    return db.query(User).filter(User.email == email.lower().strip()).first()


def sp_login_success(db: Session, user: User) -> User:
    if uses_mysql():
        try:
            db.execute(text("CALL sp_login_success(:user_id)"), {"user_id": user.user_id})
            db.commit()
        except OperationalError as exc:
            db.rollback()
            _raise_from_sql(exc)
        db.refresh(user)
        return user

    user.last_login_at = utcnow()
    _log(db, user.user_id, "login", "user", user.user_id)
    db.commit()
    db.refresh(user)
    return user


def sp_create_user_token(db: Session, user: User, purpose: str, token_hash: str, ttl_minutes: int) -> None:
    if uses_mysql():
        try:
            db.execute(
                text("CALL sp_create_user_token(:user_id, :purpose, :token_hash, :ttl)"),
                {
                    "user_id": user.user_id,
                    "purpose": purpose,
                    "token_hash": token_hash,
                    "ttl": ttl_minutes,
                },
            )
            db.commit()
        except OperationalError as exc:
            db.rollback()
            _raise_from_sql(exc)
        return

    now = utcnow()
    for old in (
        db.query(UserToken)
        .filter(UserToken.user_id == user.user_id, UserToken.purpose == purpose, UserToken.used_at.is_(None))
        .all()
    ):
        old.used_at = now
    from datetime import timedelta

    db.add(
        UserToken(
            user_id=user.user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=ttl_minutes),
        )
    )
    db.commit()


def sp_verify_email(db: Session, token_hash: str) -> User:
    if uses_mysql():
        try:
            db.execute(text("CALL sp_verify_email(:token_hash)"), {"token_hash": token_hash})
            db.commit()
        except OperationalError as exc:
            db.rollback()
            _raise_from_sql(exc)
        row = (
            db.query(UserToken)
            .filter(UserToken.token_hash == token_hash, UserToken.purpose == "email_verify")
            .first()
        )
        if row is None:
            raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
        user = db.get(User, row.user_id)
        if user is None:
            raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
        return user

    row = (
        db.query(UserToken)
        .filter(UserToken.token_hash == token_hash, UserToken.purpose == "email_verify")
        .first()
    )
    if row is None:
        raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
    if row.used_at is not None:
        raise AuthError(400, "token_used", "Liên kết đã được dùng. Hãy yêu cầu liên kết mới.")
    if row.expires_at < utcnow():
        raise AuthError(400, "token_expired", "Liên kết hết hạn. Hãy yêu cầu liên kết mới.")
    user = db.get(User, row.user_id)
    if user is None:
        raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
    row.used_at = utcnow()
    user.email_verified_at = utcnow()
    _log(db, user.user_id, "email_verified", "user", user.user_id)
    db.commit()
    db.refresh(user)
    return user


def sp_reset_password(db: Session, token_hash: str, new_password_hash: str) -> User:
    if uses_mysql():
        try:
            db.execute(
                text("CALL sp_reset_password(:token_hash, :pw)"),
                {"token_hash": token_hash, "pw": new_password_hash},
            )
            db.commit()
        except OperationalError as exc:
            db.rollback()
            _raise_from_sql(exc)
        row = (
            db.query(UserToken)
            .filter(UserToken.token_hash == token_hash, UserToken.purpose == "password_reset")
            .first()
        )
        if row is None:
            raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
        user = db.get(User, row.user_id)
        if user is None:
            raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
        return user

    row = (
        db.query(UserToken)
        .filter(UserToken.token_hash == token_hash, UserToken.purpose == "password_reset")
        .first()
    )
    if row is None:
        raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
    if row.used_at is not None:
        raise AuthError(400, "token_used", "Liên kết đã được dùng. Hãy yêu cầu liên kết mới.")
    if row.expires_at < utcnow():
        raise AuthError(400, "token_expired", "Liên kết hết hạn. Hãy yêu cầu liên kết mới.")
    user = db.get(User, row.user_id)
    if user is None:
        raise AuthError(400, "invalid_token", "Liên kết không hợp lệ.")
    now = utcnow()
    user.password_hash = new_password_hash
    for tok in (
        db.query(UserToken)
        .filter(UserToken.user_id == user.user_id, UserToken.purpose == "password_reset", UserToken.used_at.is_(None))
        .all()
    ):
        tok.used_at = now
    _log(db, user.user_id, "password_reset", "user", user.user_id)
    db.commit()
    db.refresh(user)
    return user
