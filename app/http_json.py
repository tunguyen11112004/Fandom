from flask import jsonify, request
from pydantic import ValidationError

from app.errors import AuthError


def parse_body(schema):
    payload = request.get_json(silent=True)
    if payload is None:
        raise AuthError(400, "invalid_json", "Body JSON không hợp lệ.")
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(part) for part in first.get("loc", []) if part != "body")
        msg = first.get("msg", "Dữ liệu không hợp lệ.")
        raise AuthError(422, "validation_error", f"{loc}: {msg}" if loc else msg)


def user_public(user) -> dict:
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "session_version": user.session_version,
        "is_active": user.is_active,
        "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def ok(data=None, message=None, status=200):
    body = {"ok": True}
    if message is not None:
        body["message"] = message
    if data is not None:
        body["data"] = data
    return jsonify(body), status
