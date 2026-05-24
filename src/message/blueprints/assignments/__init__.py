from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from ...authz import require_capability
from ...extensions import db
from ...models import DutyAssignment
from ...schemas.roster import SwapSchema

bp = Blueprint("assignments", __name__)
swap_schema = SwapSchema()


@bp.route("/swap", methods=["POST"])
@jwt_required()
@require_capability("manage_rosters")
def swap_assignments():
    try:
        data = swap_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    date = data["date"]
    changes = data["changes"]

    for change in changes:
        existing = DutyAssignment.query.filter_by(
            duty_id=change["duty_id"], person_id=change["from_person_id"], date=date
        ).first()
        if not existing:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": (
                        f"No assignment for duty {change['duty_id']} "
                        f"person {change['from_person_id']} on {date}"
                    ),
                }
            }, 404

        conflict = DutyAssignment.query.filter(
            DutyAssignment.duty_id == change["duty_id"],
            DutyAssignment.person_id == change["to_person_id"],
            DutyAssignment.date == date,
            DutyAssignment.id != existing.id,
        ).first()
        if conflict:
            return {
                "error": {
                    "code": "CONFLICT",
                    "message": (
                        f"Person {change['to_person_id']} is already assigned "
                        f"to duty {change['duty_id']} on {date}"
                    ),
                }
            }, 409

    for change in changes:
        assignment = DutyAssignment.query.filter_by(
            duty_id=change["duty_id"], person_id=change["from_person_id"], date=date
        ).first()
        assignment.person_id = change["to_person_id"]

    db.session.commit()
    return {"data": {"status": "swapped", "changes": len(changes)}}, 200


@bp.route("/<int:id>")
@jwt_required()
def get_assignment(id):
    a = db.session.get(DutyAssignment, id) or abort(404)
    return {
        "data": {
            "id": a.id,
            "duty_id": a.duty_id,
            "person_id": a.person_id,
            "date": str(a.date),
            "notes": a.notes,
        }
    }, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_assignment(id):
    from ...authz import _current_user

    a = db.session.get(DutyAssignment, id) or abort(404)
    user = _current_user()
    if not (user and (user.is_super_admin or user.has_capability("manage_rosters"))):
        return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403

    db.session.delete(a)
    db.session.commit()
    return "", 204
