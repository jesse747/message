from flask import Blueprint, request, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from ...authz import require_capability
from ...extensions import db
from ...models import Flock, FlockMember, Person
from ...schemas.flock import FlockSchema, FlockMemberSchema, FlockMemberUpdateSchema

bp = Blueprint("flocks", __name__)
flock_schema = FlockSchema()
member_schema = FlockMemberSchema()
member_update_schema = FlockMemberUpdateSchema()


def _flock_data(f):
    return {
        "id": f.id,
        "name": f.name,
        "description": f.description,
        "team_id": f.team_id,
        "member_count": FlockMember.query.filter_by(flock_id=f.id).count(),
    }


@bp.route("")
@jwt_required()
def list_flocks():
    q = request.args.get("q", "")
    query = Flock.query
    if q:
        query = query.filter(Flock.name.ilike(f"%{q}%"))
    flocks = query.order_by(Flock.name).all()
    return {"data": [_flock_data(f) for f in flocks]}, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("manage_flocks")
def create_flock():
    try:
        data = flock_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    flock = Flock(**data, created_by=int(get_jwt_identity()))
    db.session.add(flock)
    db.session.commit()
    return {"data": _flock_data(flock)}, 201


@bp.route("/<int:id>")
@jwt_required()
def get_flock(id):
    flock = db.session.get(Flock, id) or abort(404)
    members = FlockMember.query.filter_by(flock_id=id).all()
    return {
        "data": {
            **_flock_data(flock),
            "members": [
                {
                    "person_id": m.person_id,
                    "first_name": m.person.first_name if m.person else None,
                    "last_name": m.person.last_name if m.person else None,
                    "role": m.role,
                    "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                }
                for m in members
            ],
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_flocks")
def update_flock(id):
    flock = db.session.get(Flock, id) or abort(404)
    data = request.get_json(silent=True) or {}
    if "name" in data:
        flock.name = data["name"]
    if "description" in data:
        flock.description = data["description"]
    if "team_id" in data:
        flock.team_id = data["team_id"]
    db.session.commit()
    return {"data": _flock_data(flock)}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_flocks")
def delete_flock(id):
    flock = db.session.get(Flock, id) or abort(404)
    db.session.delete(flock)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>/members")
@jwt_required()
def list_members(id):
    db.session.get(Flock, id) or abort(404)
    members = FlockMember.query.filter_by(flock_id=id).order_by(FlockMember.joined_at).all()
    return {
        "data": [
            {
                "id": m.id,
                "person_id": m.person_id,
                "first_name": m.person.first_name if m.person else None,
                "last_name": m.person.last_name if m.person else None,
                "role": m.role,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                "notes": m.notes,
            }
            for m in members
        ]
    }, 200


@bp.route("/<int:id>/members", methods=["POST"])
@jwt_required()
@require_capability("manage_flocks")
def add_member(id):
    db.session.get(Flock, id) or abort(404)
    try:
        data = member_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    db.session.get(Person, data["person_id"]) or abort(404)
    if FlockMember.query.filter_by(person_id=data["person_id"]).first():
        return {"error": {"code": "CONFLICT", "message": "Person already belongs to a flock"}}, 409

    member = FlockMember(flock_id=id, **data)
    db.session.add(member)
    db.session.commit()
    return {"data": {"id": member.id, "person_id": member.person_id, "role": member.role}}, 201


@bp.route("/<int:id>/members/<int:person_id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_flocks")
def update_member(id, person_id):
    member = FlockMember.query.filter_by(flock_id=id, person_id=person_id).first_or_404()
    try:
        data = member_update_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    member.role = data["role"]
    if "notes" in data:
        member.notes = data["notes"]
    db.session.commit()
    return {"data": {"id": member.id, "person_id": member.person_id, "role": member.role}}, 200


@bp.route("/<int:id>/members/<int:person_id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_flocks")
def remove_member(id, person_id):
    member = FlockMember.query.filter_by(flock_id=id, person_id=person_id).first_or_404()
    db.session.delete(member)
    db.session.commit()
    return "", 204
