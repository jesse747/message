import hashlib
import secrets
import datetime as dt
from datetime import UTC, datetime

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import Schema, fields, validate
from marshmallow import ValidationError as MarshmallowError

from ...extensions import db, limiter
from ...models import AuthAttempt, InviteToken, Person, RefreshToken, User
from ...models.user_permission import INTERNAL_TO_CAPABILITY

bp = Blueprint("auth", __name__)


class RegisterSchema(Schema):
    invite_code = fields.String(required=True, validate=validate.Length(min=1))
    email = fields.Email(required=True)
    username = fields.String(required=True, validate=validate.Length(min=2, max=80))
    password = fields.String(required=True, validate=validate.Length(min=6))


class LoginSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)


register_schema = RegisterSchema()
login_schema = LoginSchema()


def _token_response(user):
    access = create_access_token(identity=str(user.id))
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC).replace(hour=0, minute=0, second=0)
        + dt.timedelta(days=30),
    )
    db.session.add(refresh)
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": "admin" if user.is_super_admin or user.permissions else "member",
        },
        "access_token": access,
        "refresh_token": raw_token,
    }


def _record_auth(username, user_id, outcome, reason=None):
    db.session.add(
        AuthAttempt(
            user_id=user_id,
            username_attempted=username,
            ip_address=request.remote_addr or "",
            user_agent=request.headers.get("User-Agent", "")[:500],
            outcome=outcome,
            failure_reason=reason,
        )
    )


def _get_user_capabilities(user):
    if user.is_super_admin:
        return [
            "edit_directory",
            "manage_announcements",
            "manage_teams",
            "manage_groups",
            "manage_rosters",
            "manage_flocks",
            "manage_events",
            "manage_organization",
            "manage_users",
            "manage_files",
        ]
    caps = []
    for perm in user.permissions:
        cap = INTERNAL_TO_CAPABILITY.get(perm.permission)
        if cap:
            caps.append(cap)
    return caps


_limiter = limiter.shared_limit("5 per minute", scope="auth")


@bp.route("/users", methods=["POST"])
@_limiter
def register():
    try:
        data = register_schema.load(request.json)
    except MarshmallowError as e:
        msg = {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}
        return {"error": msg}, 422

    invite = InviteToken.query.filter_by(code=data["invite_code"]).first()
    if not invite or not invite.is_valid:
        msg = "Invite is invalid, expired, or already used"
        return {"error": {"code": "GONE", "message": msg}}, 410

    if invite.email != data["email"]:
        msg = "Email does not match invite"
        return {"error": {"code": "VALIDATION_ERROR", "message": msg}}, 422

    if User.query.filter_by(username=data["username"]).first():
        return {"error": {"code": "CONFLICT", "message": "Username already in use"}}, 409

    person = db.session.get(Person, invite.person_id)
    if not person:
        return {"error": {"code": "NOT_FOUND", "message": "Person record not found"}}, 404

    user = User(
        username=data["username"],
        email=data["email"],
        display_name=person.first_name,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()

    person.user_id = user.id
    person.created_by = user.id
    invite.use()
    db.session.commit()

    return {"data": _token_response(user)}, 201


@bp.route("/sessions", methods=["POST"])
@_limiter
def login():
    try:
        data = login_schema.load(request.json)
    except MarshmallowError as e:
        msg = {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}
        return {"error": msg}, 422

    user = User.query.filter(
        (User.username == data["username"]) | (User.email == data["username"])
    ).first()

    if not user or not user.check_password(data["password"]):
        _record_auth(data["username"], user.id if user else None, "failure", "bad_password")
        db.session.commit()
        return {"error": {"code": "UNAUTHORIZED", "message": "Invalid username or password"}}, 401

    _record_auth(data["username"], user.id, "success")
    db.session.commit()
    return {"data": _token_response(user)}, 200


@bp.route("/sessions", methods=["DELETE"])
def logout():
    data = request.get_json(silent=True) or {}
    raw_token = data.get("refresh_token", "")
    if not raw_token:
        return {"error": {"code": "BAD_REQUEST", "message": "refresh_token required"}}, 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = RefreshToken.query.filter_by(token_hash=token_hash).first()
    if token:
        token.revoke()
        db.session.commit()
    return "", 204


@bp.route("/tokens", methods=["POST"])
def refresh():
    data = request.get_json(silent=True) or {}
    raw_token = data.get("refresh_token", "")
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = RefreshToken.query.filter_by(token_hash=token_hash).first()

    if not token or not token.is_valid:
        return {"error": {"code": "UNAUTHORIZED", "message": "Invalid or expired refresh token"}}, 401

    token.revoke()
    new_access = create_access_token(identity=str(token.user_id))
    new_raw = secrets.token_urlsafe(48)
    new_hash = hashlib.sha256(new_raw.encode()).hexdigest()
    db.session.add(
        RefreshToken(
            user_id=token.user_id,
            token_hash=new_hash,
            expires_at=datetime.now(UTC).replace(hour=0, minute=0, second=0)
            + __import__("datetime").timedelta(days=30),
        )
    )
    db.session.commit()
    return {"data": {"access_token": new_access, "refresh_token": new_raw}}, 200


@bp.route("/user", methods=["GET"])
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = db.session.get(User, uid)
    if not user:
        return {"error": {"code": "NOT_FOUND", "message": "User not found"}}, 404

    return {
        "data": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "avatar": user.avatar,
            "role": "admin" if user.is_super_admin else "member",
            "capabilities": _get_user_capabilities(user),
        }
    }, 200
