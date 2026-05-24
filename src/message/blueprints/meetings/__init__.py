from flask import Blueprint, request, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from ...extensions import db
from ...models import GroupMember, Meeting, Person, User
from ...schemas.meeting import MeetingSchema

bp = Blueprint("meetings", __name__)
meeting_schema = MeetingSchema()


def _meeting_data(m):
    return {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "team_id": m.team_id,
        "group_id": m.group_id,
        "day_of_week": m.day_of_week,
        "time": str(m.time) if m.time else None,
        "duration_minutes": m.duration_minutes,
        "location": m.location,
        "frequency": m.frequency,
        "is_active": m.is_active,
    }


@bp.route("/<int:id>")
@jwt_required()
def get_meeting(id):
    meeting = db.session.get(Meeting, id) or abort(404)
    return {"data": _meeting_data(meeting)}, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
def update_meeting(id):
    meeting = db.session.get(Meeting, id) or abort(404)
    user_id = int(get_jwt_identity())

    if meeting.team_id:
        user = db.session.get(User, user_id)
        if not (user and user.has_capability("manage_teams")):
            return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403
    if meeting.group_id:
        person = Person.query.filter_by(user_id=user_id).first()
        is_admin = person and GroupMember.query.filter_by(
            group_id=meeting.group_id, person_id=person.id, role="admin"
        ).first()
        if not is_admin:
            return {"error": {"code": "FORBIDDEN", "message": "Group admin access required"}}, 403

    try:
        data = meeting_schema.load(request.json, partial=True)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    for key, val in data.items():
        setattr(meeting, key, val)
    db.session.commit()
    return {"data": _meeting_data(meeting)}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_meeting(id):
    meeting = db.session.get(Meeting, id) or abort(404)
    user_id = int(get_jwt_identity())

    if meeting.team_id:
        user = db.session.get(User, user_id)
        if not (user and user.has_capability("manage_teams")):
            return {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}, 403
    if meeting.group_id:
        person = Person.query.filter_by(user_id=user_id).first()
        is_admin = person and GroupMember.query.filter_by(
            group_id=meeting.group_id, person_id=person.id, role="admin"
        ).first()
        if not is_admin:
            return {"error": {"code": "FORBIDDEN", "message": "Group admin access required"}}, 403

    db.session.delete(meeting)
    db.session.commit()
    return "", 204
