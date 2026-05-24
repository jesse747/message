from flask import Blueprint, abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy import or_

from ...authz import require_capability
from ...extensions import db
from ...models import Flock, FlockMember, Person
from ...schemas.flock import FlockSchema

bp = Blueprint("flocks", __name__)
flock_schema = FlockSchema()


def _flock_data(f):
    return {
        "id": f.id,
        "name": f.name,
        "description": f.description,
        "team_id": f.team_id,
        "shepherd_id": f.shepherd_id,
        "shepherd_name": f.shepherd.full_name if f.shepherd else None,
        "member_count": FlockMember.query.filter_by(flock_id=f.id).count(),
    }


def _check_shepherd_uniqueness(shepherd_id, exclude_flock_id=None):
    if shepherd_id is None:
        return None
    query = Flock.query.filter_by(shepherd_id=shepherd_id)
    if exclude_flock_id:
        query = query.filter(Flock.id != exclude_flock_id)
    return query.first()


@bp.route("")
@jwt_required()
def list_flocks():
    """List flocks with optional search.
    ---
    tags:
      - Flocks
    security:
      - Bearer: []
    parameters:
      - name: q
        in: query
        schema: {type: string}
      - name: page
        in: query
        schema: {type: integer, default: 1}
      - name: limit
        in: query
        schema: {type: integer, default: 20, maximum: 100}
    responses:
      200:
        description: Paginated list of flocks
    """
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = Flock.query
    if q:
        query = query.filter(Flock.name.ilike(f"%{q}%"))

    total = query.count()
    flocks = (
        query.order_by(Flock.name)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "data": [_flock_data(f) for f in flocks],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("manage_flocks")
def create_flock():
    try:
        data = flock_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    shepherd_id = data.pop("shepherd_id", None)
    if shepherd_id and _check_shepherd_uniqueness(shepherd_id):
        return {
            "error": {
                "code": "CONFLICT",
                "message": "Person already shepherds another flock",
            }
        }, 409

    flock = Flock(**data, created_by=int(get_jwt_identity()))
    if shepherd_id:
        flock.shepherd_id = shepherd_id
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
                    "notes": m.notes,
                    "joined_at": str(m.joined_at) if m.joined_at else None,
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

    try:
        data = flock_schema.load(request.json, partial=True)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    shepherd_id = data.pop("shepherd_id", None)
    if shepherd_id and _check_shepherd_uniqueness(shepherd_id, id):
        return {
            "error": {
                "code": "CONFLICT",
                "message": "Person already shepherds another flock",
            }
        }, 409

    for key, val in data.items():
        setattr(flock, key, val)
    if "shepherd_id" in (request.get_json(silent=True) or {}):
        flock.shepherd_id = shepherd_id
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
    members = (
        FlockMember.query.filter_by(flock_id=id)
        .order_by(FlockMember.joined_at)
        .all()
    )
    return {
        "data": [
            {
                "id": m.id,
                "person_id": m.person_id,
                "first_name": m.person.first_name if m.person else None,
                "last_name": m.person.last_name if m.person else None,
                "notes": m.notes,
                "joined_at": str(m.joined_at) if m.joined_at else None,
            }
            for m in members
        ]
    }, 200


@bp.route("/<int:id>/members", methods=["POST"])
@jwt_required()
@require_capability("manage_flocks")
def add_member(id):
    db.session.get(Flock, id) or abort(404)
    payload = request.get_json(silent=True) or {}
    person_ids = payload.get("person_ids")
    single_id = payload.get("person_id")

    if person_ids is not None:
        return _add_members_batch(id, person_ids)
    if single_id is not None:
        return _add_member_single(id, single_id)

    return {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "person_id or person_ids required",
        }
    }, 422


def _add_member_single(flock_id, person_id):
    db.session.get(Person, person_id) or abort(404)
    if FlockMember.query.filter_by(person_id=person_id).first():
        return {
            "error": {
                "code": "CONFLICT",
                "message": "Person already belongs to a flock",
            }
        }, 409

    member = FlockMember(flock_id=flock_id, person_id=person_id)
    db.session.add(member)
    db.session.commit()
    return {"data": {"id": member.id, "person_id": member.person_id}}, 201


def _add_members_batch(flock_id, person_ids):
    if not isinstance(person_ids, list) or len(person_ids) == 0:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "person_ids must be a non-empty array",
            }
        }, 422

    unique_ids = list(dict.fromkeys(person_ids))
    persons = Person.query.filter(
        Person.id.in_(unique_ids)
    ).all()
    if len(persons) != len(unique_ids):
        return {
            "error": {"code": "NOT_FOUND", "message": "One or more persons not found"}
        }, 404

    existing = FlockMember.query.filter(
        FlockMember.person_id.in_(unique_ids)
    ).all()
    if existing:
        conflict_ids = [m.person_id for m in existing]
        return {
            "error": {
                "code": "CONFLICT",
                "message": f"Persons already belong to a flock: {conflict_ids}",
            }
        }, 409

    members = [
        FlockMember(flock_id=flock_id, person_id=pid)
        for pid in unique_ids
    ]
    db.session.add_all(members)
    db.session.commit()
    return {
        "data": {
            "added": len(members),
            "members": [
                {"id": m.id, "person_id": m.person_id} for m in members
            ],
        }
    }, 201


@bp.route("/<int:id>/members/<int:person_id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_flocks")
def update_member(id, person_id):
    member = FlockMember.query.filter_by(
        flock_id=id, person_id=person_id
    ).first_or_404()
    data = request.get_json(silent=True) or {}
    if "notes" in data:
        member.notes = data["notes"]
    db.session.commit()
    return {
        "data": {
            "id": member.id,
            "person_id": member.person_id,
            "notes": member.notes,
        }
    }, 200


@bp.route("/<int:id>/members/<int:person_id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_flocks")
def remove_member(id, person_id):
    member = FlockMember.query.filter_by(
        flock_id=id, person_id=person_id
    ).first_or_404()
    db.session.delete(member)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>/available-members")
@jwt_required()
def available_members(id):
    db.session.get(Flock, id) or abort(404)
    q = request.args.get("q", "")
    membership_status = request.args.get("membership_status")

    subq = (
        FlockMember.query.with_entities(FlockMember.person_id)
        .subquery()
        .select()
    )
    query = Person.query.filter(Person.id.notin_(subq))

    if q:
        query = query.filter(
            or_(
                Person.first_name.ilike(f"%{q}%"),
                Person.last_name.ilike(f"%{q}%"),
                Person.email_personal.ilike(f"%{q}%"),
            )
        )
    if membership_status:
        query = query.filter(Person.membership_status == membership_status)

    persons = query.order_by(Person.last_name, Person.first_name).limit(100).all()
    return {
        "data": [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "email_personal": p.email_personal,
                "membership_status": p.membership_status,
                "membership_type": p.membership_type,
            }
            for p in persons
        ]
    }, 200
