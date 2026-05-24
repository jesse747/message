import datetime as dt
import hashlib
import secrets
from datetime import UTC, datetime

from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import Schema, fields, validate
from marshmallow import ValidationError as MarshmallowError

from ...email import send_password_reset_email
from ...extensions import db, limiter
from ...models import (
    AuthAttempt,
    InviteToken,
    PasswordResetToken,
    Person,
    RefreshToken,
    User,
)
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


class PasswordResetRequestSchema(Schema):
    email = fields.Email(required=True)


class PasswordResetConfirmSchema(Schema):
    token = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, validate=validate.Length(min=6))


register_schema = RegisterSchema()
login_schema = LoginSchema()
password_reset_request_schema = PasswordResetRequestSchema()
password_reset_confirm_schema = PasswordResetConfirmSchema()


def _set_refresh_cookie(response, raw_token):
    response.set_cookie(
        "refresh_token",
        raw_token,
        httponly=True,
        secure=current_app.config.get("COOKIE_SECURE", False),
        samesite="Lax",
        path=f"{current_app.config['API_PREFIX']}/auth",
        max_age=int(dt.timedelta(days=30).total_seconds()),
    )


def _clear_refresh_cookie(response):
    response.set_cookie(
        "refresh_token",
        "",
        httponly=True,
        secure=current_app.config.get("COOKIE_SECURE", False),
        samesite="Lax",
        path=f"{current_app.config['API_PREFIX']}/auth",
        max_age=0,
    )


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
    body = {
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": "admin" if user.is_super_admin or user.permissions else "member",
        },
        "access_token": access,
    }
    response = make_response(jsonify({"data": body}))
    _set_refresh_cookie(response, raw_token)
    return response


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
    """Register a new user via invite code.
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [invite_code, email, username, password]
            properties:
              invite_code:
                type: string
                description: The invitation token
              email:
                type: string
                format: email
              username:
                type: string
                minLength: 2
                maxLength: 80
              password:
                type: string
                minLength: 6
    responses:
      201:
        description: User registered. Sets refresh token cookie.
      409:
        description: Username or email already in use
      410:
        description: Invite is invalid, expired, or already used
      422:
        description: Validation error
    """
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

    if User.query.filter_by(email=data["email"]).first():
        return {"error": {"code": "CONFLICT", "message": "Email already in use"}}, 409

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
    invite.use()
    db.session.commit()

    response = _token_response(user)
    response.status_code = 201
    return response


@bp.route("/sessions", methods=["POST"])
@_limiter
def login():
    """Login with username/email and password.
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [username, password]
            properties:
              username:
                type: string
                description: Username or email address
              password:
                type: string
    responses:
      200:
        description: Login successful. Sets refresh token cookie.
      401:
        description: Invalid credentials
      422:
        description: Validation error
      429:
        description: Rate limited
    """
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
    response = _token_response(user)
    return response


@bp.route("/sessions", methods=["DELETE"])
def logout():
    """Logout — revoke refresh token and clear cookie.
    ---
    tags:
      - Auth
    responses:
      204:
        description: Logged out successfully
      400:
        description: No session cookie present
    """
    raw_token = request.cookies.get("refresh_token", "")
    if not raw_token:
        return {"error": {"code": "BAD_REQUEST", "message": "No session"}}, 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = RefreshToken.query.filter_by(token_hash=token_hash).first()
    if token:
        token.revoke()
        db.session.commit()
    response = make_response("", 204)
    _clear_refresh_cookie(response)
    return response


@bp.route("/tokens", methods=["POST"])
def refresh():
    """Refresh access token using refresh token cookie.
    ---
    tags:
      - Auth
    responses:
      200:
        description: New access token issued. Sets new refresh cookie.
      401:
        description: Invalid or expired refresh token
    """
    raw_token = request.cookies.get("refresh_token", "")
    if not raw_token:
        return {
            "error": {
                "code": "UNAUTHORIZED",
                "message": "No refresh token",
            }
        }, 401

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = RefreshToken.query.filter_by(token_hash=token_hash).first()

    if not token or not token.is_valid:
        return {
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid or expired refresh token",
            }
        }, 401

    token.revoke()
    new_access = create_access_token(identity=str(token.user_id))
    new_raw = secrets.token_urlsafe(48)
    new_hash = hashlib.sha256(new_raw.encode()).hexdigest()
    db.session.add(
        RefreshToken(
            user_id=token.user_id,
            token_hash=new_hash,
            expires_at=datetime.now(UTC).replace(hour=0, minute=0, second=0)
            + dt.timedelta(days=30),
        )
    )
    db.session.commit()
    response = make_response(jsonify({"data": {"access_token": new_access}}))
    _set_refresh_cookie(response, new_raw)
    return response


@bp.route("/user", methods=["GET"])
@jwt_required()
def me():
    """Get the current authenticated user's profile.
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: User profile with capabilities
      401:
        description: Not authenticated
    """
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


@bp.route("/password-reset", methods=["POST"])
@_limiter
def request_password_reset():
    """Request a password reset email. Always returns 200 to prevent email enumeration.
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [email]
            properties:
              email:
                type: string
                format: email
    responses:
      200:
        description: Email sent if address is registered
      422:
        description: Validation error
      429:
        description: Rate limited
    """
    try:
        data = password_reset_request_schema.load(request.json)
    except MarshmallowError as e:
        msg = {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}
        return {"error": msg}, 422

    user = User.query.filter_by(email=data["email"]).first()
    if not user:
        return {"data": {"message": "If the email is registered, a reset link has been sent."}}, 200

    code = secrets.token_urlsafe(32)
    token = PasswordResetToken(
        code=code,
        user_id=user.id,
        email=user.email,
        expires_at=datetime.now(UTC) + dt.timedelta(hours=1),
    )
    db.session.add(token)
    db.session.commit()

    send_password_reset_email(token)

    return {"data": {"message": "If the email is registered, a reset link has been sent."}}, 200


@bp.route("/password-reset/confirm", methods=["POST"])
@_limiter
def confirm_password_reset():
    """Confirm password reset with token and new password.
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [token, password]
            properties:
              token:
                type: string
                description: Password reset token from email
              password:
                type: string
                minLength: 6
    responses:
      200:
        description: Password reset successfully
      410:
        description: Token invalid, expired, or already used
      422:
        description: Validation error
      429:
        description: Rate limited
    """
    try:
        data = password_reset_confirm_schema.load(request.json)
    except MarshmallowError as e:
        msg = {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}
        return {"error": msg}, 422

    token = PasswordResetToken.query.filter_by(code=data["token"]).first()
    if not token or not token.is_valid:
        msg = "Reset token is invalid, expired, or already used"
        return {"error": {"code": "GONE", "message": msg}}, 410

    user = db.session.get(User, token.user_id)
    if not user:
        return {"error": {"code": "NOT_FOUND", "message": "User not found"}}, 404

    user.set_password(data["password"])
    token.use()
    db.session.commit()

    return {"data": {"message": "Password has been reset successfully."}}, 200
