import secrets
from datetime import UTC, datetime, timedelta

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ...extensions import db
from ...models import AuthAttempt, InviteToken, Person, User

bp = Blueprint("admin", __name__)


def _require_admin():
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not (user and (user.is_super_admin or user.has_capability("manage_users"))):
        return None
    return user


@bp.route("/auth-attempts")
@jwt_required()
def list_auth_attempts():
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not (user and (user.is_super_admin or user.has_capability("manage_organization"))):
        return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403

    outcome = request.args.get("outcome")
    ip = request.args.get("ip")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 100)

    query = AuthAttempt.query
    if outcome:
        query = query.filter(AuthAttempt.outcome == outcome)
    if ip:
        query = query.filter(AuthAttempt.ip_address == ip)

    total = query.count()
    query = query.order_by(AuthAttempt.created_at.desc())
    attempts = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [
            {
                "id": a.id,
                "username": a.username_attempted,
                "ip": a.ip_address,
                "outcome": a.outcome,
                "failure_reason": a.failure_reason,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in attempts
        ],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("/invites", methods=["POST"])
@jwt_required()
def create_invite():
    admin = _require_admin()
    if admin is None:
        return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403

    data = request.get_json(silent=True) or {}
    person_id = data.get("person_id")
    email = data.get("email")
    expires_in_days = data.get("expires_in_days", 7)

    if not person_id or not email:
        msg = "person_id and email are required"
        return {"error": {"code": "VALIDATION_ERROR", "message": msg}}, 422

    person = db.session.get(Person, person_id)
    if not person:
        return {"error": {"code": "NOT_FOUND", "message": "Person not found"}}, 404

    if Person.query.filter(Person.id == person_id, Person.user_id.isnot(None)).first():
        return {"error": {"code": "CONFLICT", "message": "Person already has a user account"}}, 409

    code = secrets.token_urlsafe(32)
    invite = InviteToken(
        code=code,
        person_id=person.id,
        email=email,
        created_by=admin.id,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
    )
    db.session.add(invite)
    db.session.commit()

    return {
        "data": {
            "id": invite.id,
            "code": invite.code,
            "person_id": invite.person_id,
            "email": invite.email,
            "created_by": invite.created_by,
            "created_at": invite.created_at.isoformat() if invite.created_at else None,
            "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
            "is_active": invite.is_active,
            "is_used": invite.is_used,
            "is_expired": invite.is_expired,
        }
    }, 201


@bp.route("/invites", methods=["GET"])
@jwt_required()
def list_invites():
    admin = _require_admin()
    if admin is None:
        return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403

    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 100)

    now = datetime.now(UTC)
    query = InviteToken.query
    if status == "active":
        query = query.filter(
            InviteToken.is_active.is_(True),
            InviteToken.used_at.is_(None),
            InviteToken.expires_at > now,
        )
    elif status == "used":
        query = query.filter(InviteToken.used_at.isnot(None))
    elif status == "expired":
        query = query.filter(
            InviteToken.is_active.is_(True),
            InviteToken.used_at.is_(None),
            InviteToken.expires_at <= now,
        )

    total = query.count()
    query = query.order_by(InviteToken.created_at.desc())
    invites = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [
            {
                "id": i.id,
                "code": i.code,
                "person_id": i.person_id,
                "email": i.email,
                "created_by": i.created_by,
                "created_at": i.created_at.isoformat() if i.created_at else None,
                "expires_at": i.expires_at.isoformat() if i.expires_at else None,
                "used_at": i.used_at.isoformat() if i.used_at else None,
                "is_active": i.is_active,
                "is_used": i.is_used,
                "is_expired": i.is_expired,
            }
            for i in invites
        ],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("/invites/<int:invite_id>", methods=["GET"])
@jwt_required()
def get_invite(invite_id):
    admin = _require_admin()
    if admin is None:
        return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403

    invite = db.session.get(InviteToken, invite_id)
    if not invite:
        return {"error": {"code": "NOT_FOUND", "message": "Invite not found"}}, 404

    return {
        "data": {
            "id": invite.id,
            "code": invite.code,
            "person_id": invite.person_id,
            "email": invite.email,
            "created_by": invite.created_by,
            "created_at": invite.created_at.isoformat() if invite.created_at else None,
            "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
            "used_at": invite.used_at.isoformat() if invite.used_at else None,
            "is_active": invite.is_active,
            "is_used": invite.is_used,
            "is_expired": invite.is_expired,
        }
    }, 200


@bp.route("/invites/<int:invite_id>", methods=["DELETE"])
@jwt_required()
def revoke_invite(invite_id):
    admin = _require_admin()
    if admin is None:
        return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403

    invite = db.session.get(InviteToken, invite_id)
    if not invite:
        return {"error": {"code": "NOT_FOUND", "message": "Invite not found"}}, 404

    if invite.is_used:
        msg = "Cannot revoke an already-used invite"
        return {"error": {"code": "CONFLICT", "message": msg}}, 409

    invite.is_active = False
    db.session.commit()
    return "", 204
