import os
import uuid
from datetime import UTC, datetime

from flask import Blueprint, abort, current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ...authz import require_capability, require_team_admin
from ...extensions import db
from ...models import File, Meeting, MeetingInstance, Person, PersonTeam, Post, Team, User
from ...schemas.meeting import MeetingSchema
from ...schemas.meeting_instance import MeetingInstanceSchema, MeetingInstanceUpdateSchema
from ...schemas.team import TeamSchema, TeamUpdateSchema

bp = Blueprint("teams", __name__)
team_schema = TeamSchema()
team_update_schema = TeamUpdateSchema()
instance_schema = MeetingInstanceSchema()
instance_update_schema = MeetingInstanceUpdateSchema()


@bp.route("")
@jwt_required()
def list_teams():
    q = request.args.get("q", "")
    query = Team.query
    if q:
        query = query.filter(Team.name.ilike(f"%{q}%"))
    teams = query.order_by(Team.name).all()
    return {
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "parent_id": t.parent_id,
                "team_admin_id": t.team_admin_id,
                "person_count": PersonTeam.query.filter_by(team_id=t.id).count(),
            }
            for t in teams
        ]
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("manage_teams")
def create_team():
    try:
        data = team_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    if Team.query.filter_by(name=data["name"]).first():
        return {"error": {"code": "CONFLICT", "message": "Team name already exists"}}, 409

    team = Team(**data)
    team.created_by = int(get_jwt_identity())
    db.session.add(team)
    db.session.commit()
    return {
        "data": {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "parent_id": team.parent_id,
            "team_admin_id": team.team_admin_id,
        }
    }, 201


@bp.route("/<int:id>")
@jwt_required()
def get_team(id):
    team = db.session.get(Team, id) or abort(404)
    meetings = team.meetings or []
    return {
        "data": {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "parent_id": team.parent_id,
            "parent_name": team.parent.name if team.parent else None,
            "children": [{"id": c.id, "name": c.name} for c in team.children],
            "team_admin_id": team.team_admin_id,
            "team_admin_name": (
                f"{team.team_admin.first_name} {team.team_admin.last_name}"
                if team.team_admin
                else None
            ),
            "person_count": PersonTeam.query.filter_by(team_id=id).count(),
            "meetings": [
                {
                    "id": m.id,
                    "name": m.name,
                    "day_of_week": m.day_of_week,
                    "time": str(m.time) if m.time else None,
                    "frequency": m.frequency,
                    "location": m.location,
                    "instances": [
                        {
                            "id": i.id,
                            "date": str(i.date),
                            "time": str(i.time) if i.time else None,
                            "location": i.location,
                            "cancelled": i.cancelled,
                        }
                        for i in m.instances
                    ],
                }
                for m in meetings
            ],
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_team_admin
def update_team(id):
    team = db.session.get(Team, id) or abort(404)
    try:
        data = team_update_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    if (
        "name" in data
        and data["name"] != team.name
        and Team.query.filter_by(name=data["name"]).first()
    ):
        return {"error": {"code": "CONFLICT", "message": "Team name already exists"}}, 409

    for key, val in data.items():
        setattr(team, key, val)
    db.session.commit()
    return {
        "data": {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "parent_id": team.parent_id,
            "team_admin_id": team.team_admin_id,
        }
    }, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_teams")
def delete_team(id):
    team = db.session.get(Team, id) or abort(404)
    db.session.delete(team)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>/persons")
@jwt_required()
def team_persons(id):
    db.session.get(Team, id) or abort(404)
    memberships = PersonTeam.query.filter_by(team_id=id).all()
    return {
        "data": [
            {
                "person_id": pt.person_id,
                "first_name": pt.person.first_name if pt.person else None,
                "last_name": pt.person.last_name if pt.person else None,
                "role": pt.role,
                "joined_at": pt.joined_at.isoformat() if pt.joined_at else None,
            }
            for pt in memberships
        ]
    }, 200


@bp.route("/<int:id>/persons", methods=["POST"])
@jwt_required()
@require_team_admin
def add_team_person(id):
    db.session.get(Team, id) or abort(404)
    data = request.get_json(silent=True) or {}
    person_id = data.get("person_id")
    if not person_id:
        return {"error": {"code": "BAD_REQUEST", "message": "person_id required"}}, 400

    db.session.get(Person, person_id) or abort(404)
    if PersonTeam.query.filter_by(team_id=id, person_id=person_id).first():
        return {"error": {"code": "CONFLICT", "message": "Person already in this team"}}, 409

    pt = PersonTeam(team_id=id, person_id=person_id, role=data.get("role"))
    db.session.add(pt)
    db.session.commit()
    return {"data": {"team_id": id, "person_id": person_id, "role": pt.role}}, 201


@bp.route("/<int:id>/persons/<int:person_id>", methods=["DELETE"])
@jwt_required()
@require_team_admin
def remove_team_person(id, person_id):
    pt = PersonTeam.query.filter_by(team_id=id, person_id=person_id).first_or_404()
    db.session.delete(pt)
    db.session.commit()
    return "", 204


# ── Team meetings ──


@bp.route("/<int:team_id>/meetings")
@jwt_required()
def list_team_meetings(team_id):
    db.session.get(Team, team_id) or abort(404)
    meetings = (
        Meeting.query.filter_by(team_id=team_id)
        .order_by(Meeting.day_of_week, Meeting.time)
        .all()
    )
    return {
        "data": [
            {
                "id": m.id,
                "name": m.name,
                "day_of_week": m.day_of_week,
                "time": str(m.time) if m.time else None,
                "frequency": m.frequency,
                "location": m.location,
            }
            for m in meetings
        ]
    }, 200


@bp.route("/<int:team_id>/meetings", methods=["POST"])
@jwt_required()
@require_team_admin
def create_team_meeting(team_id):
    db.session.get(Team, team_id) or abort(404)
    try:
        data = MeetingSchema().load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    data.pop("team_id", None)
    data.pop("group_id", None)
    meeting = Meeting(**data, team_id=team_id)
    db.session.add(meeting)
    db.session.flush()
    instances = meeting.generate_instances()
    for inst in instances:
        db.session.add(inst)
    db.session.commit()
    return {
        "data": {
            "id": meeting.id,
            "name": meeting.name,
            "day_of_week": meeting.day_of_week,
            "time": str(meeting.time) if meeting.time else None,
            "frequency": meeting.frequency,
            "location": meeting.location,
            "instances": [
                {
                    "id": i.id,
                    "date": str(i.date),
                    "time": str(i.time) if i.time else None,
                    "location": i.location,
                    "cancelled": i.cancelled,
                }
                for i in instances
            ],
        }
    }, 201


# ── Team meeting instances ──


def _instance_detail(i):
    return {
        "id": i.id,
        "date": str(i.date),
        "time": str(i.time) if i.time else None,
        "location": i.location,
        "cancelled": i.cancelled,
        "notes": i.notes,
        "cancellation_message": i.cancellation_message,
        "files": [
            {"id": f.id, "name": f.name, "type": f.type}
            for f in i.files
        ],
    }


@bp.route("/<int:team_id>/meetings/<int:mid>/instances")
@jwt_required()
def list_meeting_instances(team_id, mid):  # noqa: ARG001
    db.session.get(Meeting, mid) or abort(404)
    instances = MeetingInstance.query.filter_by(meeting_id=mid).order_by(MeetingInstance.date).all()
    return {"data": [_instance_detail(i) for i in instances]}, 200


@bp.route("/<int:team_id>/meetings/<int:mid>/instances", methods=["POST"])
@jwt_required()
@require_team_admin
def create_meeting_instance(team_id, mid):  # noqa: ARG001
    meeting = db.session.get(Meeting, mid) or abort(404)
    body = request.get_json(silent=True) or {}

    if body.get("generate"):
        count = body.get("count", 12)
        instances = meeting.generate_instances(count=count)
        for inst in instances:
            db.session.add(inst)
        db.session.commit()
        return {"data": [_instance_detail(i) for i in instances]}, 201

    try:
        data = instance_schema.load(body)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    data.pop("meeting_id", None)
    inst = MeetingInstance(**data, meeting_id=mid)
    db.session.add(inst)
    db.session.commit()
    return {"data": _instance_detail(inst)}, 201


@bp.route("/<int:team_id>/meetings/<int:mid>/instances/<int:iid>", methods=["PATCH"])
@jwt_required()
@require_team_admin
def update_meeting_instance(team_id, mid, iid):
    inst = db.session.get(MeetingInstance, iid) or abort(404)
    if inst.meeting_id != mid:
        return {"error": {"code": "NOT_FOUND", "message": "Instance not found"}}, 404

    try:
        data = instance_update_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    cancelled = data.pop("cancelled", None)
    cancellation_message = data.pop("cancellation_message", None)

    for key, val in data.items():
        setattr(inst, key, val)

    if cancelled is not None:
        inst.cancelled = cancelled

    if cancellation_message is not None and inst.cancelled:
        inst.cancellation_message = cancellation_message
        user_id = int(get_jwt_identity())
        post = Post(
            content=cancellation_message,
            team_id=team_id,
            meeting_instance_id=inst.id,
            author_id=user_id,
        )
        db.session.add(post)

    db.session.commit()
    return {"data": _instance_detail(inst)}, 200


@bp.route("/<int:team_id>/meetings/<int:mid>/instances/<int:iid>", methods=["DELETE"])
@jwt_required()
@require_team_admin
def delete_meeting_instance(team_id, mid, iid):  # noqa: ARG001
    inst = db.session.get(MeetingInstance, iid) or abort(404)
    if inst.meeting_id != mid:
        return {"error": {"code": "NOT_FOUND", "message": "Instance not found"}}, 404
    db.session.delete(inst)
    db.session.commit()
    return "", 204


@bp.route("/<int:team_id>/meetings/<int:mid>/instances/<int:iid>/files")
@jwt_required()
def list_instance_files(team_id, mid, iid):  # noqa: ARG001
    db.session.get(MeetingInstance, iid) or abort(404)
    files = File.query.filter_by(meeting_instance_id=iid).order_by(File.uploaded_at.desc()).all()
    return {
        "data": [
            {
                "id": f.id,
                "name": f.name,
                "type": f.type,
                "size_kb": round(f.size / 1024, 1),
                "url": f"/api/v1/files/{f.id}",
                "uploaded_by": f.uploaded_by,
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
            }
            for f in files
        ]
    }, 200


@bp.route("/<int:team_id>/meetings/<int:mid>/instances/<int:iid>/files", methods=["POST"])
@jwt_required()
@require_team_admin
def upload_instance_file(team_id, mid, iid):  # noqa: ARG001
    db.session.get(MeetingInstance, iid) or abort(404)
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return {
            "error": {
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": "multipart/form-data required",
            }
        }, 415

    files = request.files.getlist("file") or [request.files.get("file")]
    files = [f for f in files if f and f.filename]
    if not files:
        return {"error": {"code": "BAD_REQUEST", "message": "No file provided"}}, 400

    user_id = int(get_jwt_identity())
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    saved = []

    for f in files:
        ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else ""
        storage_name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(upload_dir, storage_name))
        file_obj = File(
            name=f.filename,
            storage_name=storage_name,
            type=f.content_type or "application/octet-stream",
            size=os.path.getsize(os.path.join(upload_dir, storage_name)),
            meeting_instance_id=iid,
            uploaded_by=user_id,
            uploaded_at=datetime.now(UTC),
        )
        db.session.add(file_obj)
        saved.append(file_obj)

    db.session.commit()
    return {
        "data": [
            {
                "id": f.id,
                "name": f.name,
                "type": f.type,
                "size_kb": round(f.size / 1024, 1),
                "url": f"/api/v1/files/{f.id}",
            }
            for f in saved
        ]
    }, 201


@bp.route(
    "/<int:team_id>/meetings/<int:mid>/instances/<int:iid>/files/<int:fid>",
    methods=["DELETE"],
)
@jwt_required()
@require_team_admin
def delete_instance_file(team_id, mid, iid, fid):  # noqa: ARG001
    file_obj = db.session.get(File, fid) or abort(404)
    if file_obj.meeting_instance_id != iid:
        return {"error": {"code": "NOT_FOUND", "message": "File not found"}}, 404
    storage_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_obj.storage_name)
    if os.path.exists(storage_path):
        os.remove(storage_path)
    db.session.delete(file_obj)
    db.session.commit()
    return "", 204


# ── Team files ──


@bp.route("/<int:team_id>/files")
@jwt_required()
def list_team_files(team_id):
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = File.query.filter_by(team_id=team_id)
    if q:
        query = query.filter(File.name.ilike(f"%{q}%"))

    total = query.count()
    files = query.order_by(File.uploaded_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [
            {
                "id": f.id,
                "name": f.name,
                "type": f.type,
                "size_kb": round(f.size / 1024, 1),
                "url": f"/api/v1/files/{f.id}",
                "uploaded_by": {
                    "id": f.uploaded_by,
                    "name": f.uploader.display_name if f.uploader else None,
                },
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
            }
            for f in files
        ],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("/<int:team_id>/files", methods=["POST"])
@jwt_required()
def upload_team_file(team_id):
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return {
            "error": {
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": "multipart/form-data required",
            }
        }, 415

    files = request.files.getlist("file") or [request.files.get("file")]
    files = [f for f in files if f and f.filename]

    if not files:
        return {"error": {"code": "BAD_REQUEST", "message": "No file provided"}}, 400

    user_id = int(get_jwt_identity())
    saved = []
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    for f in files:
        ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else ""
        storage_name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(upload_dir, storage_name))
        file_obj = File(
            name=f.filename,
            storage_name=storage_name,
            type=f.content_type or "application/octet-stream",
            size=os.path.getsize(os.path.join(upload_dir, storage_name)),
            team_id=team_id,
            uploaded_by=user_id,
            uploaded_at=datetime.now(UTC),
        )
        db.session.add(file_obj)
        saved.append(file_obj)

    db.session.commit()
    return {
        "data": [
            {
                "id": f.id,
                "name": f.name,
                "type": f.type,
                "size_kb": round(f.size / 1024, 1),
                "url": f"/api/v1/files/{f.id}",
            }
            for f in saved
        ]
    }, 201


# ── Team posts ──


@bp.route("/<int:team_id>/posts")
@jwt_required()
def list_team_posts(team_id):
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)
    query = Post.query.filter_by(team_id=team_id)
    total = query.count()
    posts = query.order_by(Post.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [
            {
                "id": p.id,
                "content": p.content,
                "author": {
                    "id": p.author_id,
                    "display_name": p.author.display_name if p.author else None,
                },
                "files": [{"id": f.id, "name": f.name, "type": f.type} for f in (p.files or [])],
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("/<int:team_id>/posts", methods=["POST"])
@jwt_required()
def create_team_post(team_id):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    person = Person.query.filter_by(user_id=user_id).first()

    is_member = user.is_super_admin or (
        person
        and PersonTeam.query.filter_by(
            team_id=team_id, person_id=person.id
        ).first()
    )
    if not is_member:
        return {"error": {"code": "FORBIDDEN", "message": "Not a member of this team"}}, 403

    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return {"error": {"code": "BAD_REQUEST", "message": "content required"}}, 400

    post = Post(
        content=content,
        team_id=team_id,
        author_id=user_id,
        show_on_bulletin=data.get("show_on_bulletin", False),
    )
    db.session.add(post)
    db.session.commit()
    return {
        "data": {
            "id": post.id,
            "content": post.content,
            "author": {
                "id": post.author_id,
                "display_name": post.author.display_name if post.author else None,
            },
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }
    }, 201
