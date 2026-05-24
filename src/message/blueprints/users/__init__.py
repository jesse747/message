from flask import Blueprint, abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import or_

from ...extensions import db
from ...models import User

bp = Blueprint("users", __name__)


@bp.route("")
@jwt_required()
def list_users():
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = User.query
    if q:
        query = query.filter(
            or_(
                User.username.ilike(f"%{q}%"),
                User.display_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
            )
        )
    query = query.order_by(User.username)
    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "data": [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "email": u.email,
                "avatar": u.avatar,
                "is_super_admin": u.is_super_admin,
            }
            for u in users
        ],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("/<int:id>")
@jwt_required()
def get_user(id):
    user = db.session.get(User, id) or abort(404)
    return {
        "data": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "avatar": user.avatar,
            "is_super_admin": user.is_super_admin,
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
def update_user(id):
    current_id = int(get_jwt_identity())
    user = db.session.get(User, id) or abort(404)

    if current_id != id:
        return {"error": {"code": "FORBIDDEN", "message": "Cannot update other users"}}, 403

    data = request.get_json(silent=True) or {}
    if "display_name" in data:
        user.display_name = data["display_name"]
    if "avatar" in data:
        user.avatar = data["avatar"]

    db.session.commit()
    return {
        "data": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "avatar": user.avatar,
        }
    }, 200
