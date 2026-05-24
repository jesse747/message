import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from ...authz import require_group_admin
from ...extensions import db
from ...models import File, Group, GroupMember, Meeting, MeetingInstance, Person, Post, User
from ...schemas.group import GroupSchema, GroupUpdateSchema, GroupMemberSchema, GroupMemberUpdateSchema
from ...schemas.meeting import MeetingSchema
from ...schemas.meeting_instance import MeetingInstanceSchema, MeetingInstanceUpdateSchema

bp = Blueprint("groups", __name__)
group_schema = GroupSchema()
group_update_schema = GroupUpdateSchema()
member_schema = GroupMemberSchema()
member_update_schema = GroupMemberUpdateSchema()
instance_schema = MeetingInstanceSchema()
instance_update_schema = MeetingInstanceUpdateSchema()


@bp.route("")
@jwt_required()
def list_groups():
    q = request.args.get("q", "")
    query = Group.query
    if q:
        query = query.filter(Group.name.ilike(f"%{q}%"))
    groups = query.order_by(Group.name).all()
    return {
        "data": [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "is_public": g.is_public,
                "member_count": GroupMember.query.filter_by(group_id=g.id).count(),
            }
            for g in groups
        ]
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
def create_group():
    try:
        data = group_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    group = Group(**data)
    group.created_by = int(get_jwt_identity())
    db.session.add(group)
    db.session.flush()

    user = db.session.get(User, get_jwt_identity())
    person = Person.query.filter_by(user_id=user.id).first()
    if person:
        gm = GroupMember(group_id=group.id, person_id=person.id, role="admin")
        db.session.add(gm)

    db.session.commit()
    return {"data": {"id": group.id, "name": group.name, "description": group.description, "is_public": group.is_public}}, 201


@bp.route("/<int:id>")
@jwt_required()
def get_group(id):
    group = db.session.get(Group, id) or abort(404)
    meetings = group.meetings or []
    return {
        "data": {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "is_public": group.is_public,
            "member_count": GroupMember.query.filter_by(group_id=id).count(),
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


@bp.route("/<int:id>/join", methods=["POST"])
@jwt_required()
def join_group(id):
    group = db.session.get(Group, id) or abort(404)
    if not group.is_public:
        return {"error": {"code": "FORBIDDEN", "message": "Group is private"}}, 403

    user_id = int(get_jwt_identity())
    person = Person.query.filter_by(user_id=user_id).first()
    if not person:
        return {"error": {"code": "BAD_REQUEST", "message": "No person record linked to your account"}}, 400

    if GroupMember.query.filter_by(group_id=id, person_id=person.id).first():
        return {"error": {"code": "CONFLICT", "message": "Already a member of this group"}}, 409

    gm = GroupMember(group_id=id, person_id=person.id, role="member")
    db.session.add(gm)
    db.session.commit()
    return {"data": {"person_id": person.id, "role": "member"}}, 201


@bp.route("/<int:id>/leave", methods=["POST"])
@jwt_required()
def leave_group(id):
    db.session.get(Group, id) or abort(404)

    user_id = int(get_jwt_identity())
    person = Person.query.filter_by(user_id=user_id).first()
    if not person:
        return {"error": {"code": "BAD_REQUEST", "message": "No person record linked to your account"}}, 400

    gm = GroupMember.query.filter_by(group_id=id, person_id=person.id).first()
    if not gm:
        return {"error": {"code": "NOT_FOUND", "message": "Not a member of this group"}}, 404

    db.session.delete(gm)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_group_admin
def update_group(id):
    group = db.session.get(Group, id) or abort(404)
    try:
        data = group_update_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    for key, val in data.items():
        setattr(group, key, val)
    db.session.commit()
    return {"data": {"id": group.id, "name": group.name, "description": group.description}}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_group_admin
def delete_group(id):
    group = db.session.get(Group, id) or abort(404)
    db.session.delete(group)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>/members")
@jwt_required()
def list_members(id):
    db.session.get(Group, id) or abort(404)
    members = GroupMember.query.filter_by(group_id=id).all()
    return {
        "data": [
            {
                "id": gm.id,
                "person_id": gm.person_id,
                "first_name": gm.person.first_name if gm.person else None,
                "last_name": gm.person.last_name if gm.person else None,
                "role": gm.role,
                "joined_at": gm.joined_at.isoformat() if gm.joined_at else None,
            }
            for gm in members
        ]
    }, 200


@bp.route("/<int:id>/members", methods=["POST"])
@jwt_required()
@require_group_admin
def add_member(id):
    try:
        data = member_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    db.session.get(Person, data["person_id"]) or abort(404)
    if GroupMember.query.filter_by(group_id=id, person_id=data["person_id"]).first():
        return {"error": {"code": "CONFLICT", "message": "Person already in this group"}}, 409

    gm = GroupMember(group_id=id, **data)
    db.session.add(gm)
    db.session.commit()
    return {"data": {"id": gm.id, "person_id": gm.person_id, "role": gm.role}}, 201


@bp.route("/<int:id>/members/<int:person_id>", methods=["PATCH"])
@jwt_required()
@require_group_admin
def update_member(id, person_id):
    gm = GroupMember.query.filter_by(group_id=id, person_id=person_id).first_or_404()
    try:
        data = member_update_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    gm.role = data["role"]
    db.session.commit()
    return {"data": {"id": gm.id, "person_id": gm.person_id, "role": gm.role}}, 200


@bp.route("/<int:id>/members/<int:person_id>", methods=["DELETE"])
@jwt_required()
@require_group_admin
def remove_member(id, person_id):
    gm = GroupMember.query.filter_by(group_id=id, person_id=person_id).first_or_404()
    db.session.delete(gm)
    db.session.commit()
    return "", 204


# ── Group meetings ──


@bp.route("/<int:group_id>/meetings")
@jwt_required()
def list_group_meetings(group_id):
    db.session.get(Group, group_id) or abort(404)
    meetings = Meeting.query.filter_by(group_id=group_id).order_by(Meeting.day_of_week, Meeting.time).all()
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


@bp.route("/<int:group_id>/meetings", methods=["POST"])
@jwt_required()
@require_group_admin
def create_group_meeting(group_id):
    try:
        data = MeetingSchema().load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    data.pop("group_id", None)
    data.pop("team_id", None)
    meeting = Meeting(**data, group_id=group_id)
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


# ── Group meeting instances ──


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


@bp.route("/<int:group_id>/meetings/<int:mid>/instances")
@jwt_required()
def list_meeting_instances(group_id, mid):
    db.session.get(Meeting, mid) or abort(404)
    instances = MeetingInstance.query.filter_by(meeting_id=mid).order_by(MeetingInstance.date).all()
    return {"data": [_instance_detail(i) for i in instances]}, 200


@bp.route("/<int:group_id>/meetings/<int:mid>/instances", methods=["POST"])
@jwt_required()
@require_group_admin
def create_meeting_instance(group_id, mid):
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
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

    data.pop("meeting_id", None)
    inst = MeetingInstance(**data, meeting_id=mid)
    db.session.add(inst)
    db.session.commit()
    return {"data": _instance_detail(inst)}, 201


@bp.route("/<int:group_id>/meetings/<int:mid>/instances/<int:iid>", methods=["PATCH"])
@jwt_required()
@require_group_admin
def update_meeting_instance(group_id, mid, iid):
    inst = db.session.get(MeetingInstance, iid) or abort(404)
    if inst.meeting_id != mid:
        return {"error": {"code": "NOT_FOUND", "message": "Instance not found"}}, 404

    try:
        data = instance_update_schema.load(request.json)
    except ValidationError as e:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": e.messages}}, 422

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
            group_id=group_id,
            meeting_instance_id=inst.id,
            author_id=user_id,
        )
        db.session.add(post)

    db.session.commit()
    return {"data": _instance_detail(inst)}, 200


@bp.route("/<int:group_id>/meetings/<int:mid>/instances/<int:iid>", methods=["DELETE"])
@jwt_required()
@require_group_admin
def delete_meeting_instance(group_id, mid, iid):
    inst = db.session.get(MeetingInstance, iid) or abort(404)
    if inst.meeting_id != mid:
        return {"error": {"code": "NOT_FOUND", "message": "Instance not found"}}, 404
    db.session.delete(inst)
    db.session.commit()
    return "", 204


@bp.route("/<int:group_id>/meetings/<int:mid>/instances/<int:iid>/files")
@jwt_required()
def list_instance_files(group_id, mid, iid):
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


@bp.route("/<int:group_id>/meetings/<int:mid>/instances/<int:iid>/files", methods=["POST"])
@jwt_required()
@require_group_admin
def upload_instance_file(group_id, mid, iid):
    db.session.get(MeetingInstance, iid) or abort(404)
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return {"error": {"code": "UNSUPPORTED_MEDIA_TYPE", "message": "multipart/form-data required"}}, 415

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
            uploaded_at=datetime.now(timezone.utc),
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


@bp.route("/<int:group_id>/meetings/<int:mid>/instances/<int:iid>/files/<int:fid>", methods=["DELETE"])
@jwt_required()
@require_group_admin
def delete_instance_file(group_id, mid, iid, fid):
    file_obj = db.session.get(File, fid) or abort(404)
    if file_obj.meeting_instance_id != iid:
        return {"error": {"code": "NOT_FOUND", "message": "File not found"}}, 404
    storage_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_obj.storage_name)
    if os.path.exists(storage_path):
        os.remove(storage_path)
    db.session.delete(file_obj)
    db.session.commit()
    return "", 204


# ── Group files ──


@bp.route("/<int:group_id>/files")
@jwt_required()
def list_group_files(group_id):
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = File.query.filter_by(group_id=group_id)
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
                "uploaded_by": {"id": f.uploaded_by, "name": f.uploader.display_name if f.uploader else None},
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
            }
            for f in files
        ],
        "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if total else 0},
    }, 200


@bp.route("/<int:group_id>/files", methods=["POST"])
@jwt_required()
def upload_group_file(group_id):
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return {"error": {"code": "UNSUPPORTED_MEDIA_TYPE", "message": "multipart/form-data required"}}, 415

    files = request.files.getlist("file") or [request.files.get("file")]
    files = [f for f in files if f and f.filename]

    if not files:
        return {"error": {"code": "BAD_REQUEST", "message": "No file provided"}}, 400

    user_id = int(get_jwt_identity())
    person = Person.query.filter_by(user_id=user_id).first()
    is_member = person and GroupMember.query.filter_by(group_id=group_id, person_id=person.id).first()
    if not is_member:
        user = db.session.get(User, user_id)
        if not (user and user.is_super_admin):
            return {"error": {"code": "FORBIDDEN", "message": "Not a member of this group"}}, 403

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
            group_id=group_id,
            uploaded_by=user_id,
            uploaded_at=datetime.now(timezone.utc),
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


# ── Group posts ──


@bp.route("/<int:group_id>/posts")
@jwt_required()
def list_group_posts(group_id):
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)
    query = Post.query.filter_by(group_id=group_id)
    total = query.count()
    posts = query.order_by(Post.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [
            {
                "id": p.id,
                "content": p.content,
                "author": {"id": p.author_id, "display_name": p.author.display_name if p.author else None},
                "files": [{"id": f.id, "name": f.name, "type": f.type} for f in (p.files or [])],
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ],
        "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if total else 0},
    }, 200


@bp.route("/<int:group_id>/posts", methods=["POST"])
@jwt_required()
def create_group_post(group_id):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    person = Person.query.filter_by(user_id=user_id).first()

    if not (user.is_super_admin or GroupMember.query.filter_by(group_id=group_id, person_id=person.id).first() if person else False):
        return {"error": {"code": "FORBIDDEN", "message": "Not a member of this group"}}, 403

    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return {"error": {"code": "BAD_REQUEST", "message": "content required"}}, 400

    post = Post(content=content, group_id=group_id, author_id=user_id)
    db.session.add(post)
    db.session.commit()
    return {
        "data": {
            "id": post.id,
            "content": post.content,
            "author": {"id": post.author_id, "display_name": post.author.display_name if post.author else None},
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }
    }, 201
