from datetime import date, timedelta

from flask import Blueprint, request, abort
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from ...authz import require_capability
from ...extensions import db
from ...models import Duty, DutyAssignment, DutyGroup, DutyGroupMembership
from ...schemas.roster import DutyGroupSchema, DutySchema, DutyGroupMembershipSchema, AutoAssignSchema

bp = Blueprint("duty_groups", __name__)
duty_group_schema = DutyGroupSchema()
auto_assign_schema = AutoAssignSchema()


@bp.route("")
@jwt_required()
def list_duty_groups():
    q = request.args.get("q", "")
    day_of_week = request.args.get("day_of_week", type=int)
    query = DutyGroup.query
    if q:
        query = query.filter(DutyGroup.name.ilike(f"%{q}%"))
    if day_of_week is not None:
        query = query.filter_by(day_of_week=day_of_week)
    groups = query.order_by(DutyGroup.day_of_week, DutyGroup.time).all()
    return {
        "data": [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "day_of_week": g.day_of_week,
                "time": str(g.time) if g.time else None,
                "is_active": g.is_active,
            }
            for g in groups
        ]
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("manage_rosters")
def create_duty_group():
    try:
        data = duty_group_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    g = DutyGroup(**data)
    db.session.add(g)
    db.session.commit()
    return {
        "data": {"id": g.id, "name": g.name, "day_of_week": g.day_of_week, "time": str(g.time) if g.time else None}
    }, 201


@bp.route("/<int:id>")
@jwt_required()
def get_duty_group(id):
    g = db.session.get(DutyGroup, id) or abort(404)
    duties = Duty.query.filter_by(duty_group_id=id).order_by(Duty.sort_order).all()
    memberships = DutyGroupMembership.query.filter_by(duty_group_id=id).all()
    return {
        "data": {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "day_of_week": g.day_of_week,
            "time": str(g.time) if g.time else None,
            "is_active": g.is_active,
            "duties": [
                {"id": d.id, "name": d.name, "description": d.description, "sort_order": d.sort_order, "is_active": d.is_active}
                for d in duties
            ],
            "memberships": [
                {
                    "id": m.id,
                    "person_id": m.person_id,
                    "person_name": m.person.full_name if m.person else None,
                    "date_from": str(m.date_from),
                    "date_to": str(m.date_to) if m.date_to else None,
                }
                for m in memberships
            ],
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_rosters")
def update_duty_group(id):
    g = db.session.get(DutyGroup, id) or abort(404)
    data = request.get_json(silent=True) or {}
    for key in ("name", "description", "day_of_week", "time", "is_active"):
        if key in data:
            setattr(g, key, data[key])
    db.session.commit()
    return {"data": {"id": g.id, "name": g.name}}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_rosters")
def delete_duty_group(id):
    g = db.session.get(DutyGroup, id) or abort(404)
    db.session.delete(g)
    db.session.commit()
    return "", 204


# Duties within a group
@bp.route("/<int:group_id>/duties")
@jwt_required()
def list_duties(group_id):
    db.session.get(DutyGroup, group_id) or abort(404)
    duties = Duty.query.filter_by(duty_group_id=group_id).order_by(Duty.sort_order).all()
    return {
        "data": [
            {"id": d.id, "name": d.name, "description": d.description, "sort_order": d.sort_order, "is_active": d.is_active}
            for d in duties
        ]
    }, 200


@bp.route("/<int:group_id>/duties", methods=["POST"])
@jwt_required()
@require_capability("manage_rosters")
def create_duty(group_id):
    db.session.get(DutyGroup, group_id) or abort(404)
    try:
        data = DutySchema().load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    d = Duty(**data, duty_group_id=group_id)
    db.session.add(d)
    db.session.commit()
    return {"data": {"id": d.id, "name": d.name, "duty_group_id": d.duty_group_id, "sort_order": d.sort_order}}, 201


# Memberships within a group
@bp.route("/<int:group_id>/memberships")
@jwt_required()
def list_memberships(group_id):
    db.session.get(DutyGroup, group_id) or abort(404)
    memberships = DutyGroupMembership.query.filter_by(duty_group_id=group_id).all()
    return {
        "data": [
            {
                "id": m.id,
                "person_id": m.person_id,
                "person_name": m.person.full_name if m.person else None,
                "date_from": str(m.date_from),
                "date_to": str(m.date_to) if m.date_to else None,
            }
            for m in memberships
        ]
    }, 200


@bp.route("/<int:group_id>/memberships", methods=["POST"])
@jwt_required()
@require_capability("manage_rosters")
def create_membership(group_id):
    db.session.get(DutyGroup, group_id) or abort(404)
    try:
        data = DutyGroupMembershipSchema().load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    existing = DutyGroupMembership.query.filter_by(
        duty_group_id=group_id, person_id=data["person_id"], date_from=data["date_from"]
    ).first()
    if existing:
        return {"error": {"code": "CONFLICT", "message": "Person already has a membership in this group from this date"}}, 409

    m = DutyGroupMembership(**data, duty_group_id=group_id)
    db.session.add(m)
    db.session.commit()
    return {"data": {"id": m.id, "person_id": m.person_id, "date_from": str(m.date_from)}}, 201


@bp.route("/<int:id>/auto-assign", methods=["POST"])
@jwt_required()
@require_capability("manage_rosters")
def auto_assign(id):
    group = db.session.get(DutyGroup, id) or abort(404)
    try:
        data = auto_assign_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    from_date = data["from_date"]
    to_date = data.get("to_date") or (from_date + timedelta(weeks=12))

    created, gaps = group.generate_assignments(from_date, to_date)
    for a in created:
        db.session.add(a)
    db.session.commit()

    return {
        "data": {
            "assignments_created": len(created),
            "dates_covered": len(set(a.date for a in created)),
            "gaps": gaps,
        }
    }, 201
