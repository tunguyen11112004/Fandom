from flask import Blueprint, request

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.http_json import ok, parse_body, user_public
from app.schemas import (
    EmailIn,
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    ResetPasswordIn,
    VerifyEmailIn,
)
from app.services_auth import (
    GENERIC_RESET_SENT,
    login,
    logout,
    refresh_tokens,
    register_user,
    request_password_reset,
    resend_verification,
    reset_password,
    verify_email,
)

bp = Blueprint("auth", __name__)
bp.strict_slashes = False

AUTH_CATALOG = {
    "register": {"method": "POST", "path": "/register"},
    "verify_email_get": {"method": "GET", "path": "/verify-email?token="},
    "verify_email_post": {"method": "POST", "path": "/verify-email"},
    "resend_verification": {"method": "POST", "path": "/resend-verification"},
    "login": {"method": "POST", "path": "/login"},
    "admin_login": {"method": "POST", "path": "/admin/login"},
    "logout": {"method": "POST", "path": "/logout"},
    "refresh": {"method": "POST", "path": "/refresh"},
    "me": {"method": "GET", "path": "/me"},
    "forgot_password": {"method": "POST", "path": "/forgot-password"},
    "reset_password_get": {"method": "GET", "path": "/reset-password?token="},
    "reset_password_post": {"method": "POST", "path": "/reset-password"},
}


@bp.get("/")
def auth_index():
    prefix = f"{settings.api_prefix}/auth"
    return ok(
        data={"prefix": prefix, "endpoints": AUTH_CATALOG},
        message="Use POST /register or POST /login. Open /auth-ui to try it in the browser.",
    )


@bp.post("/register")
def register():
    body = parse_body(RegisterIn)
    user, raw_token = register_user(get_db(), body.name, body.email, body.password, body.password_confirm)
    payload = user_public(user)
    if settings.email_backend == "console":
        payload["debug_verify_token"] = raw_token
    return ok(data=payload, message="Account created. Verify your email before signing in.")


@bp.post("/login")
def member_login():
    body = parse_body(LoginIn)
    tokens = login(get_db(), body.email, body.password, require_admin=False)
    return ok(data=tokens)


@bp.post("/admin/login")
def admin_login():
    body = parse_body(LoginIn)
    tokens = login(get_db(), body.email, body.password, require_admin=True)
    return ok(data=tokens)


@bp.post("/logout")
def member_logout():
    body = parse_body(LogoutIn)
    logout(get_db(), body.refresh_token)
    return ok(message="Signed out.")


@bp.post("/refresh")
def refresh():
    body = parse_body(RefreshIn)
    tokens = refresh_tokens(get_db(), body.refresh_token)
    return ok(data=tokens)


@bp.get("/me")
def me():
    return ok(data=user_public(get_current_user()))


@bp.get("/verify-email")
def verify_email_get():
    token = request.args.get("token", "")
    verify_email(get_db(), token)
    return ok(message="Email verified. Sign in.")


@bp.post("/verify-email")
def verify_email_post():
    body = parse_body(VerifyEmailIn)
    verify_email(get_db(), body.token)
    return ok(message="Email verified. Sign in.")


@bp.post("/resend-verification")
def resend():
    body = parse_body(EmailIn)
    raw = resend_verification(get_db(), body.email)
    extra = None
    if settings.email_backend == "console" and raw:
        extra = {"debug_verify_token": raw}
    return ok(data=extra, message="If that email is valid and unverified, a link has been sent.")


@bp.post("/forgot-password")
def forgot():
    body = parse_body(EmailIn)
    raw = request_password_reset(get_db(), body.email)
    extra = None
    if settings.email_backend == "console" and raw:
        extra = {"debug_reset_token": raw}
    return ok(data=extra, message=GENERIC_RESET_SENT)


@bp.post("/reset-password")
def reset():
    body = parse_body(ResetPasswordIn)
    reset_password(get_db(), body.token, body.password, body.password_confirm)
    return ok(message="Your new password is ready. Sign in.")


@bp.get("/reset-password")
def reset_hint():
    token = request.args.get("token", "")
    return ok(
        data={"token": token},
        message="Gui POST /auth/reset-password voi token, password, password_confirm.",
    )
