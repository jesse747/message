import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, request, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from ...authz import require_capability, require_super_admin
from ...extensions import db
from ...models import Family, File, Person

bp = Blueprint("families", __name__)


def _photo_url(family):
    return f"/api/v1/files/{family.photo_file_id}/serve" if family.photo_file_id else None


def _family_detail(family):
    head = family.head_person
    return {
        "id": family.id,
        "name": family.name,
        "head_person_id": family.head_person_id,
        "head_name": f"{head.first_name} {head.last_name}" if head else None,
        "photo_url": _photo_url(family),
        "member_count": len(family.members),
        "created_at": family.created_at.isoformat() if family.created_at else None,
        "updated_at": family.updated_at.isoformat() if family.updated_at else None,
    }


def _family_with_members(family):
    head_id = family.head_person_id
    return {
        "id": family.id,
        "name": family.name,
        "head_person_id": head_id,
        "head_name": (
            f"{family.head_person.first_name} {family.head_person.last_name}"
            if family.head_person else None
        ),
        "photo_url": _photo_url(family),
        "members": [
            {
                "person_id": m.id,
                "first_name": m.first_name,
                "last_name": m.last_name,
                "role": "head" if m.id == head_id else "member",
            }
            for m in sorted(family.members, key=lambda p: (0 if p.id == head_id else 1, p.last_name, p.first_name))
        ],
        "created_at": family.created_at.isoformat() if family.created_at else None,
        "updated_at": family.updated_at.isoformat() if family.updated_at else None,
    }


@bp.route("")
@jwt_required()
def list_families():
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = Family.query
    if q:
        query = query.filter(Family.name.ilike(f"%{q}%"))

    total = query.count()
    families = query.order_by(Family.name).offset((page - 1) * limit).limit(limit).all()

    return {
        "data": [_family_detail(f) for f in families],
        "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if total else 0},
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("edit_directory")
def create_family():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    head_person_id = data.get("head_person_id")

    if not name:
        return {"error": {"code": "VALIDATION_ERROR", "message": "Name is required"}}, 422

    if head_person_id is not None:
        person = db.session.get(Person, head_person_id)
        if not person:
            return {"error": {"code": "NOT_FOUND", "message": "Head person not found"}}, 404
        existing_head = Family.query.filter(
            Family.head_person_id == head_person_id
        ).first()
        if existing_head:
            return {
                "error": {
                    "code": "CONFLICT",
                    "message": "Person is already head of another family",
                }
            }, 409

    family = Family(name=name, head_person_id=head_person_id)
    db.session.add(family)
    db.session.commit()

    return {"data": _family_detail(family)}, 201


@bp.route("/<int:id>")
@jwt_required()
def get_family(id):
    family = db.session.get(Family, id) or abort(404)
    return {"data": _family_with_members(family)}, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_capability("edit_directory")
def update_family(id):
    family = db.session.get(Family, id) or abort(404)
    data = request.get_json(silent=True) or {}

    if "name" in data:
        family.name = data["name"]

    if "head_person_id" in data:
        new_head_id = data["head_person_id"]
        if new_head_id is not None:
            person = db.session.get(Person, new_head_id)
            if not person:
                return {"error": {"code": "NOT_FOUND", "message": "Head person not found"}}, 404
            existing_head = Family.query.filter(
                Family.head_person_id == new_head_id, Family.id != id
            ).first()
            if existing_head:
                return {
                    "error": {
                        "code": "CONFLICT",
                        "message": "Person is already head of another family",
                    }
                }, 409
        family.head_person_id = new_head_id

    db.session.commit()
    return {"data": _family_detail(family)}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_super_admin
def delete_family(id):
    family = db.session.get(Family, id) or abort(404)

    if family.photo_file_id:
        photo = db.session.get(File, family.photo_file_id)
        if photo:
            storage_path = os.path.join(current_app.config["UPLOAD_FOLDER"], photo.storage_name)
            if os.path.exists(storage_path):
                os.remove(storage_path)
            db.session.delete(photo)

    Person.query.filter(Person.family_id == id).update(
        {Person.family_id: None}
    )
    db.session.delete(family)
    db.session.commit()
    return "", 204


@bp.route("/<int:id>/photo", methods=["POST"])
@jwt_required()
@require_capability("edit_directory")
def upload_family_photo(id):
    family = db.session.get(Family, id) or abort(404)

    if not request.content_type or "multipart/form-data" not in request.content_type:
        return {"error": {"code": "UNSUPPORTED_MEDIA_TYPE", "message": "multipart/form-data required"}}, 415

    f = request.files.get("file")
    if not f or not f.filename:
        return {"error": {"code": "BAD_REQUEST", "message": "No file provided"}}, 400

    ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else ""
    storage_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    f.save(os.path.join(upload_dir, storage_name))

    user_id = int(get_jwt_identity())
    file_obj = File(
        name=f.filename,
        storage_name=storage_name,
        type=f.content_type or "application/octet-stream",
        size=os.path.getsize(os.path.join(upload_dir, storage_name)),
        uploaded_by=user_id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.session.add(file_obj)
    db.session.flush()

    old_photo_id = family.photo_file_id
    family.photo_file_id = file_obj.id
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
def get_family_photo(id):
    family = db.session.get(Family, id) or abort(404)
    if not family.photo_file_id:
        return {"error": {"code": "NOT_FOUND", "message": "No photo"}}, 404

    file_obj = db.session.get(File, family.photo_file_id) or abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        file_obj.storage_name,
        mimetype=file_obj.type,
    )


@bp.route("/<int:id>/photo", methods=["DELETE"])
@jwt_required()
@require_capability("edit_directory")
def delete_family_photo(id):
    family = db.session.get(Family, id) or abort(404)
    if not family.photo_file_id:
        return {"error": {"code": "NOT_FOUND", "message": "No photo"}}, 404

    file_obj = db.session.get(File, family.photo_file_id)
    family.photo_file_id = None
    db.session.commit()

    if file_obj:
        storage_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_obj.storage_name)
        if os.path.exists(storage_path):
            os.remove(storage_path)
        db.session.delete(file_obj)
        db.session.commit()

    return "", 204
