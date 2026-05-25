import os
import uuid
from datetime import UTC, datetime

from flask import Blueprint, abort, current_app, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy import or_

from ...authz import require_capability, require_super_admin
from ...extensions import db
from ...models import (
    EventType,
    FamilyRelationship,
    File,
    GroupMember,
    Person,
    PersonEvent,
    PersonTeam,
    User,
)
from ...schemas.person import PersonSchema
from ...schemas.person_event import PersonEventSchema, PersonEventUpdateSchema

bp = Blueprint("persons", __name__)
person_schema = PersonSchema()
person_event_schema = PersonEventSchema()
person_event_update_schema = PersonEventUpdateSchema()

CONTACT_FIELDS = {
    "email_personal", "email_work", "phone_mobile", "phone_home",
    "phone_work", "address", "address_street", "address_city",
    "address_region", "address_postal_code", "address_country",
    "emergency_contact_name", "emergency_contact_phone",
    "date_of_birth", "notes",
}


def _person_detail(person):
    return {
        "id": person.id,
        "user_id": person.user_id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "email_personal": person.email_personal,
        "email_work": person.email_work,
        "phone_mobile": person.phone_mobile,
        "phone_home": person.phone_home,
        "phone_work": person.phone_work,
	"address": person.address,
        "address_street": person.address_street,
        "address_city": person.address_city,
        "address_region": person.address_region,
        "address_postal_code": person.address_postal_code,
        "address_country": person.address_country,
        "emergency_contact_name": person.emergency_contact_name,
        "emergency_contact_phone": person.emergency_contact_phone,
        "membership_status": person.membership_status,
        "membership_type": person.membership_type,
        "membership_number": person.membership_number,
        "date_of_birth": str(person.date_of_birth) if person.date_of_birth else None,
        "membership_notes": person.membership_notes,
        "notes": person.notes,
        "family_id": person.family_id,
        "family_name": person.family.name if person.family else None,
        "photo_url": (
            f"/api/v1/files/{person.photo_file_id}/serve" if person.photo_file_id else None
        ),
        "team_ids": [pt.team_id for pt in person.teams],
        "flock_ids": [fm.flock_id for fm in person.flock_memberships],
        "events": [
            {
                "id": e.id,
                "event_type_id": e.event_type_id,
                "event_type": e.event_type.name if e.event_type else None,
                "event_date": str(e.event_date),
                "location": e.location,
                "notes": e.notes,
                "file_url": e.file_url,
            }
            for e in person.events
        ],
    }


@bp.route("")
@jwt_required()
def list_persons():
    """List persons with optional search and filters.
    ---
    tags:
      - Persons
    security:
      - Bearer: []
    parameters:
      - name: q
        in: query
        schema: {type: string}
        description: Search by first name, last name, or email
      - name: team_id
        in: query
        schema: {type: integer}
      - name: membership_status
        in: query
        schema: {type: string, enum: [member, visitor, inactive, former]}
      - name: page
        in: query
        schema: {type: integer, default: 1}
      - name: limit
        in: query
        schema: {type: integer, default: 20, maximum: 100}
    responses:
      200:
        description: Paginated list of persons
    """
    q = request.args.get("q", "")
    team_id = request.args.get("team_id", type=int)
    membership_status = request.args.get("membership_status")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = Person.query
    if q:
        query = query.filter(
            or_(
                Person.first_name.ilike(f"%{q}%"),
                Person.last_name.ilike(f"%{q}%"),
                Person.email_personal.ilike(f"%{q}%"),
            )
        )
    if team_id:
        query = query.join(PersonTeam).filter(PersonTeam.team_id == team_id)
    if membership_status:
        query = query.filter(Person.membership_status == membership_status)

    total = query.count()
    persons = (
        query.order_by(Person.last_name, Person.first_name)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "data": [_person_detail(p) for p in persons],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("edit_directory")
def create_person():
    try:
        data = person_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    if (
        data.get("membership_number")
        and Person.query.filter_by(membership_number=data["membership_number"]).first()
    ):
        return {"error": {"code": "CONFLICT", "message": "Membership number already in use"}}, 409

    person = Person(**data)
    person.created_by = int(get_jwt_identity())
    db.session.add(person)
    db.session.commit()

    return {"data": _person_detail(person)}, 201


@bp.route("/<int:id>")
@jwt_required()
def get_person(id):
    person = db.session.get(Person, id) or abort(404)
    relationships = FamilyRelationship.query.filter(
        (FamilyRelationship.person_1_id == id) | (FamilyRelationship.person_2_id == id)
    ).all()

    family = person.family
    return {
        "data": {
            **_person_detail(person),
            "family": {
                "id": family.id,
                "name": family.name,
                "head_person_id": family.head_person_id,
                "head_name": (
                    f"{family.head_person.first_name} {family.head_person.last_name}"
                    if family.head_person
                    else None
                ),
                "members": [
                    {
                        "person_id": m.id,
                        "first_name": m.first_name,
                        "last_name": m.last_name,
                        "role": "head" if m.id == family.head_person_id else "member",
                    }
                    for m in family.members
                ],
            } if family else None,
            "relationships": [
                {
                    "id": r.id,
                    "person_id": r.person_2_id if r.person_1_id == id else r.person_1_id,
                    "relationship_type": r.relationship_type,
                }
                for r in relationships
            ],
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
def update_person(id):
    person = db.session.get(Person, id) or abort(404)
    current_id = int(get_jwt_identity())
    user = db.session.get(User, current_id)

    is_self = person.user_id == current_id

    if not (is_self or user.is_super_admin or user.has_capability("edit_directory")):
        return {"error": {"code": "FORBIDDEN", "message": "Cannot update this person"}}, 403

    try:
        data = person_schema.load(request.json, partial=True)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    if is_self:
        restricted = {k for k in data if k not in CONTACT_FIELDS}
        if restricted:
            return {
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Cannot update these fields on your own profile",
                }
            }, 403

    if "membership_number" in data and data["membership_number"]:
        existing = Person.query.filter(
            Person.membership_number == data["membership_number"], Person.id != id
        ).first()
        if existing:
            return {
                "error": {"code": "CONFLICT", "message": "Membership number already in use"}
            }, 409

    for key, val in data.items():
        setattr(person, key, val)
    db.session.commit()

    return {"data": _person_detail(person)}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_super_admin
def delete_person(id):
    person = db.session.get(Person, id) or abort(404)
    if person.user_id:
        user = db.session.get(User, person.user_id)
        if user and user.is_super_admin:
            return {"error": {"code": "FORBIDDEN", "message": "Cannot delete the super admin"}}, 403
    db.session.delete(person)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>/teams")
@jwt_required()
def person_teams(id):
    person = db.session.get(Person, id) or abort(404)
    return {
        "data": [
            {
                "team_id": pt.team_id,
                "team_name": pt.team.name,
                "role": pt.role,
            }
            for pt in person.teams
            if pt.team
        ]
    }, 200


@bp.route("/<int:id>/flocks")
@jwt_required()
def person_flocks(id):
    person = db.session.get(Person, id) or abort(404)
    return {
        "data": [
            {"flock_id": fm.flock_id, "flock_name": fm.flock.name, "role": fm.role}
            for fm in person.flock_memberships
            if fm.flock
        ]
    }, 200


@bp.route("/<int:id>/family")
@jwt_required()
def person_family(id):
    person = db.session.get(Person, id) or abort(404)
    family = person.family
    if not family:
        return {
            "data": {
                "id": None,
                "name": None,
                "head_person_id": None,
                "members": [
                    {
                        "person_id": person.id,
                        "first_name": person.first_name,
                        "last_name": person.last_name,
                        "role": "self",
                    }
                ],
            }
    }, 200


# ── Person events ──


@bp.route("/<int:id>/events")
@jwt_required()
def list_person_events(id):
    person = db.session.get(Person, id) or abort(404)
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = (
        PersonEvent.query.filter_by(person_id=person.id)
        .order_by(PersonEvent.event_date.desc())
    )
    total = query.count()
    events = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [
            {
                "id": e.id,
                "event_type_id": e.event_type_id,
                "event_type": e.event_type.name if e.event_type else None,
                "event_date": str(e.event_date),
                "location": e.location,
                "notes": e.notes,
                "file_url": e.file_url,
            }
            for e in events
        ],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("/<int:id>/events", methods=["POST"])
@jwt_required()
@require_capability("edit_directory")
def create_person_event(id):
    person = db.session.get(Person, id) or abort(404)

    try:
        data = person_event_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    event_type = db.session.get(EventType, data["event_type_id"])
    if not event_type:
        return {
            "error": {"code": "NOT_FOUND", "message": "Event type not found"}
        }, 404

    event = PersonEvent(
        person_id=person.id,
        event_type_id=data["event_type_id"],
        event_date=data["event_date"],
        location=data.get("location"),
        notes=data.get("notes"),
        created_by=int(get_jwt_identity()),
    )
    db.session.add(event)
    db.session.commit()
    return {
        "data": {
            "id": event.id,
            "event_type_id": event.event_type_id,
            "event_type": event.event_type.name if event.event_type else None,
            "event_date": str(event.event_date),
            "location": event.location,
            "notes": event.notes,
            "file_url": event.file_url,
        }
    }, 201


@bp.route("/<int:id>/events/<int:eid>")
@jwt_required()
def get_person_event(id, eid):
    event = PersonEvent.query.filter_by(id=eid, person_id=id).first() or abort(404)
    return {
        "data": {
            "id": event.id,
            "event_type_id": event.event_type_id,
            "event_type": event.event_type.name if event.event_type else None,
            "event_date": str(event.event_date),
            "location": event.location,
            "notes": event.notes,
            "file_url": event.file_url,
        }
    }, 200


@bp.route("/<int:id>/events/<int:eid>", methods=["PATCH"])
@jwt_required()
@require_capability("edit_directory")
def update_person_event(id, eid):
    event = PersonEvent.query.filter_by(id=eid, person_id=id).first() or abort(404)

    try:
        data = person_event_update_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    if "event_type_id" in data and not db.session.get(EventType, data["event_type_id"]):
        return {
            "error": {"code": "NOT_FOUND", "message": "Event type not found"}
        }, 404

    for key, val in data.items():
        setattr(event, key, val)
    db.session.commit()
    return {
        "data": {
            "id": event.id,
            "event_type_id": event.event_type_id,
            "event_type": event.event_type.name if event.event_type else None,
            "event_date": str(event.event_date),
            "location": event.location,
            "notes": event.notes,
            "file_url": event.file_url,
        }
    }, 200


@bp.route("/<int:id>/events/<int:eid>", methods=["DELETE"])
@jwt_required()
@require_capability("edit_directory")
def delete_person_event(id, eid):
    event = PersonEvent.query.filter_by(id=eid, person_id=id).first() or abort(404)
    db.session.delete(event)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>/events/<int:eid>/file", methods=["POST"])
@jwt_required()
@require_capability("edit_directory")
def upload_event_file(id, eid):
    event = PersonEvent.query.filter_by(id=eid, person_id=id).first() or abort(404)

    if not request.content_type or "multipart/form-data" not in request.content_type:
        return {
            "error": {
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": "multipart/form-data required",
            }
        }, 415

    f = request.files.get("file")
    if not f or not f.filename:
        return {"error": {"code": "BAD_REQUEST", "message": "No file provided"}}, 400

    user_id = int(get_jwt_identity())
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else ""
    storage_name = f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(upload_dir, storage_name))

    file_obj = File(
        name=f.filename,
        storage_name=storage_name,
        type=f.content_type or "application/octet-stream",
        size=os.path.getsize(os.path.join(upload_dir, storage_name)),
        person_event_id=event.id,
        uploaded_by=user_id,
        uploaded_at=datetime.now(UTC),
    )
    db.session.add(file_obj)
    db.session.flush()

    old_file_id = event.file_id
    event.file_id = file_obj.id
    db.session.commit()

    if old_file_id:
        old_file = db.session.get(File, old_file_id)
        if old_file:
            old_path = os.path.join(upload_dir, old_file.storage_name)
            if os.path.exists(old_path):
                os.remove(old_path)
            db.session.delete(old_file)
            db.session.commit()

    return {
        "data": {
            "id": file_obj.id,
            "name": file_obj.name,
            "type": file_obj.type,
            "size_kb": round(file_obj.size / 1024, 1),
            "url": f"/api/v1/files/{file_obj.id}",
        }
    }, 201


@bp.route("/<int:id>/events/<int:eid>/file")
@jwt_required()
def get_event_file(id, eid):
    event = PersonEvent.query.filter_by(id=eid, person_id=id).first() or abort(404)
    if not event.file_id:
        abort(404)
    file_obj = db.session.get(File, event.file_id) or abort(404)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_dir, file_obj.storage_name, as_attachment=True)


@bp.route("/<int:id>/events/<int:eid>/file", methods=["DELETE"])
@jwt_required()
@require_capability("edit_directory")
def delete_event_file(id, eid):
    event = PersonEvent.query.filter_by(id=eid, person_id=id).first() or abort(404)
    if not event.file_id:
        abort(404)
    file_obj = db.session.get(File, event.file_id) or abort(404)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(upload_dir, file_obj.storage_name)

    event.file_id = None
    db.session.delete(file_obj)
    db.session.commit()

    if os.path.exists(file_path):
        os.remove(file_path)

    return "", 204


@bp.route("/<int:id>/photo", methods=["POST"])
@jwt_required()
def upload_person_photo(id):
    person = db.session.get(Person, id) or abort(404)
    current_id = int(get_jwt_identity())
    user = db.session.get(User, current_id)

    if not (
        user.is_super_admin
        or user.has_capability("edit_directory")
        or person.user_id == current_id
    ):
        return {"error": {"code": "FORBIDDEN", "message": "Cannot update this person"}}, 403

    if not request.content_type or "multipart/form-data" not in request.content_type:
        return {
            "error": {
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": "multipart/form-data required",
            }
        }, 415

    f = request.files.get("file")
    if not f or not f.filename:
        return {"error": {"code": "BAD_REQUEST", "message": "No file provided"}}, 400

    ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else ""
    storage_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    f.save(os.path.join(upload_dir, storage_name))

    file_obj = File(
        name=f.filename,
        storage_name=storage_name,
        type=f.content_type or "application/octet-stream",
        size=os.path.getsize(os.path.join(upload_dir, storage_name)),
        uploaded_by=current_id,
        uploaded_at=datetime.now(UTC),
    )
    db.session.add(file_obj)
    db.session.flush()

    old_photo_id = person.photo_file_id
    person.photo_file_id = file_obj.id
    db.session.commit()

    if old_photo_id:
        old_file = db.session.get(File, old_photo_id)
        if old_file:
            old_path = os.path.join(upload_dir, old_file.storage_name)
            if os.path.exists(old_path):
                os.remove(old_path)
            db.session.delete(old_file)
            db.session.commit()

    return {"data": {"photo_url": f"/api/v1/files/{file_obj.id}/serve"}}, 201


@bp.route("/<int:id>/photo")
@jwt_required()
def get_person_photo(id):
    person = db.session.get(Person, id) or abort(404)
    if not person.photo_file_id:
        return {"error": {"code": "NOT_FOUND", "message": "No photo"}}, 404

    file_obj = db.session.get(File, person.photo_file_id) or abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        file_obj.storage_name,
        mimetype=file_obj.type,
    )


@bp.route("/<int:id>/photo", methods=["DELETE"])
@jwt_required()
def delete_person_photo(id):
    person = db.session.get(Person, id) or abort(404)
    current_id = int(get_jwt_identity())
    user = db.session.get(User, current_id)

    if not (
        user.is_super_admin
        or user.has_capability("edit_directory")
        or person.user_id == current_id
    ):
        return {"error": {"code": "FORBIDDEN", "message": "Cannot update this person"}}, 403

    if not person.photo_file_id:
        return {"error": {"code": "NOT_FOUND", "message": "No photo"}}, 404

    file_obj = db.session.get(File, person.photo_file_id)
    person.photo_file_id = None
    db.session.commit()

    if file_obj:
        storage_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_obj.storage_name)
        if os.path.exists(storage_path):
            os.remove(storage_path)
        db.session.delete(file_obj)
        db.session.commit()

    return "", 204


@bp.route("/<int:id>/groups")
@jwt_required()
def person_groups(id):
    db.session.get(Person, id) or abort(404)
    memberships = GroupMember.query.filter_by(person_id=id).all()
    return {
        "data": [
            {
                "group_id": gm.group_id,
                "group_name": gm.group.name if gm.group else None,
                "role": gm.role,
            }
            for gm in memberships
        ]
    }, 200


@bp.route("/<int:id>/relationships")
@jwt_required()
def person_relationships(id):
    db.session.get(Person, id) or abort(404)
    relationships = FamilyRelationship.query.filter(
        (FamilyRelationship.person_1_id == id) | (FamilyRelationship.person_2_id == id)
    ).all()
    return {
        "data": [
            {
                "id": r.id,
                "person_id": r.person_2_id if r.person_1_id == id else r.person_1_id,
                "relationship_type": r.relationship_type,
            }
            for r in relationships
        ]
    }, 200


@bp.route("/<int:id>/memberships")
@jwt_required()
def person_memberships(id):
    from ...models import DutyGroupMembership

    db.session.get(Person, id) or abort(404)
    memberships = DutyGroupMembership.query.filter_by(person_id=id).all()
    return {
        "data": [
            {
                "id": m.id,
                "duty_group_id": m.duty_group_id,
                "duty_group_name": m.duty_group.name if m.duty_group else None,
                "date_from": str(m.date_from),
                "date_to": str(m.date_to) if m.date_to else None,
            }
            for m in memberships
        ]
    }, 200
