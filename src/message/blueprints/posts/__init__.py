import os
import uuid
from datetime import UTC, datetime

from flask import Blueprint, abort, current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ...extensions import db
from ...models import File, Post, User
from ...schemas.post import PostSchema, PostUpdateSchema

bp = Blueprint("posts", __name__)
post_schema = PostSchema()
post_update_schema = PostUpdateSchema()


def _post_data(post):
    return {
        "id": post.id,
        "content": post.content,
        "team_id": post.team_id,
        "group_id": post.group_id,
        "duty_group_id": post.duty_group_id,
        "show_on_bulletin": post.show_on_bulletin,
        "author": {
            "id": post.author_id,
            "display_name": post.author.display_name if post.author else None,
        },
        "is_pinned": post.is_pinned,
        "expires_at": post.expires_at.isoformat() if post.expires_at else None,
        "files": [{"id": f.id, "name": f.name, "type": f.type} for f in (post.files or [])],
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


def _can_edit_post(post, user_id):
    if post.author_id == user_id:
        return True
    user = db.session.get(User, user_id)
    return user and (user.is_super_admin or user.has_capability("manage_announcements"))


@bp.route("")
@jwt_required()
def list_posts():
    show_expired = request.args.get("show_expired", "").lower() == "true"
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    from datetime import datetime

    query = Post.query.filter(
        (
            Post.team_id.is_(None)
            & Post.group_id.is_(None)
            & Post.duty_group_id.is_(None)
            & Post.meeting_instance_id.is_(None)
        )
        | Post.show_on_bulletin.is_(True)
    )
    if not show_expired:
        query = query.filter((Post.expires_at.is_(None)) | (Post.expires_at > datetime.now(UTC)))

    total = query.count()
    posts = (
        query.order_by(Post.is_pinned.desc(), Post.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "data": [_post_data(p) for p in posts],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
def create_post():
    user_id = int(get_jwt_identity())

    try:
        data = post_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    post = Post(**data, author_id=user_id)
    db.session.add(post)
    db.session.commit()
    return {"data": _post_data(post)}, 201


@bp.route("/<int:id>")
@jwt_required()
def get_post(id):
    post = db.session.get(Post, id) or abort(404)
    return {"data": _post_data(post)}, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
def update_post(id):
    post = db.session.get(Post, id) or abort(404)
    user_id = int(get_jwt_identity())

    if not _can_edit_post(post, user_id):
        return {"error": {"code": "FORBIDDEN", "message": "Cannot edit this post"}}, 403

    try:
        data = post_update_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    for key, val in data.items():
        setattr(post, key, val)
    db.session.commit()
    return {"data": _post_data(post)}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_post(id):
    post = db.session.get(Post, id) or abort(404)
    user_id = int(get_jwt_identity())

    if not _can_edit_post(post, user_id):
        return {"error": {"code": "FORBIDDEN", "message": "Cannot delete this post"}}, 403

    db.session.delete(post)
    db.session.commit()
    return "", 204


@bp.route("/<int:post_id>/files", methods=["POST"])
@jwt_required()
def upload_post_file(post_id):
    db.session.get(Post, post_id) or abort(404)
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
            post_id=post_id,
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
