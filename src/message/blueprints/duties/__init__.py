from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from ...authz import require_capability
from ...extensions import db
from ...models import Duty, DutyAssignment
from ...schemas.roster import DutyAssignmentSchema, DutySchema

bp = Blueprint("duties", __name__)
duty_schema = DutySchema()
assignment_schema = DutyAssignmentSchema()


@bp.route("/<int:id>")
@jwt_required()
def get_duty(id):
    d = db.session.get(Duty, id) or abort(404)
    return {
        "data": {
            "id": d.id,
            "duty_group_id": d.duty_group_id,
            "name": d.name,
            "description": d.description,
            "sort_order": d.sort_order,
            "is_active": d.is_active,
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_rosters")
def update_duty(id):
    d = db.session.get(Duty, id) or abort(404)
    data = request.get_json(silent=True) or {}
    for key in ("name", "description", "sort_order", "is_active"):
        if key in data:
            setattr(d, key, data[key])
    db.session.commit()
    return {"data": {"id": d.id, "name": d.name, "sort_order": d.sort_order}}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_rosters")
def delete_duty(id):
    d = db.session.get(Duty, id) or abort(404)
    db.session.delete(d)
    db.session.commit()
    return "", 204


@bp.route("/<int:duty_id>/assignments")
@jwt_required()
def list_assignments(duty_id):
    db.session.get(Duty, duty_id) or abort(404)
    person_id = request.args.get("person_id", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = DutyAssignment.query.filter_by(duty_id=duty_id)
    if person_id:
        query = query.filter_by(person_id=person_id)
    if date_from:
        query = query.filter(DutyAssignment.date >= date_from)
    if date_to:
        query = query.filter(DutyAssignment.date <= date_to)

    assignments = query.order_by(DutyAssignment.date).all()
    return {
        "data": [
            {
                "id": a.id,
                "person_id": a.person_id,
                "person_name": a.person.full_name if a.person else None,
                "date": str(a.date),
                "notes": a.notes,
            }
            for a in assignments
        ]
    }, 200


@bp.route("/<int:duty_id>/assignments", methods=["POST"])
@jwt_required()
@require_capability("manage_rosters")
def create_assignment(duty_id):
    db.session.get(Duty, duty_id) or abort(404)
    try:
        data = assignment_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    a = DutyAssignment(**data, duty_id=duty_id)
    db.session.add(a)
    db.session.commit()
    return {
        "data": {
            "id": a.id,
            "person_id": a.person_id,
            "duty_id": duty_id,
            "date": str(a.date),
        }
    }, 201
