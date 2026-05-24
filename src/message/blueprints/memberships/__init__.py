from flask import Blueprint, abort
from flask_jwt_extended import jwt_required

from ...extensions import db
from ...models import DutyGroupMembership

bp = Blueprint("memberships", __name__)


@bp.route("/<int:id>")
@jwt_required()
def get_membership(id):
    m = db.session.get(DutyGroupMembership, id) or abort(404)
    return {
        "data": {
            "id": m.id,
            "duty_group_id": m.duty_group_id,
            "person_id": m.person_id,
            "date_from": str(m.date_from),
            "date_to": str(m.date_to) if m.date_to else None,
        }
    }, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_membership(id):
    from ...authz import require_capability, _current_user
    from ...models import User

    m = db.session.get(DutyGroupMembership, id) or abort(404)
    user = _current_user()
    if not (user and (user.is_super_admin or user.has_capability("manage_rosters"))):
        return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403

    db.session.delete(m)
    db.session.commit()
    return "", 204
