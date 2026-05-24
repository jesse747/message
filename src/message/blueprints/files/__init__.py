import os

from flask import Blueprint, abort, current_app, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required

from ...extensions import db
from ...models import File, User

bp = Blueprint("files", __name__)


def _file_data(f):
    return {
        "id": f.id,
        "name": f.name,
        "type": f.type,
        "size_kb": round(f.size / 1024, 1) if f.size else 0,
        "url": f"/api/v1/files/{f.id}",
        "uploaded_by": {
            "id": f.uploaded_by,
            "name": f.uploader.display_name if f.uploader else None,
        },
        "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
    }


@bp.route("/<int:id>")
@jwt_required()
def get_file(id):
    file_obj = db.session.get(File, id) or abort(404)
    return {"data": _file_data(file_obj)}, 200


@bp.route("/<int:id>/download")
@jwt_required()
def download_file(id):
    file_obj = db.session.get(File, id) or abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        file_obj.storage_name,
        download_name=file_obj.name,
        as_attachment=True,
    )


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_file(id):
    file_obj = db.session.get(File, id) or abort(404)
    user_id = int(get_jwt_identity())

    if file_obj.uploaded_by != user_id:
        user = db.session.get(User, user_id)
        if not (user and (user.is_super_admin or user.has_capability("manage_files"))):
            return {"error": {"code": "FORBIDDEN", "message": "Cannot delete this file"}}, 403

    db.session.delete(file_obj)
    db.session.commit()

    storage_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_obj.storage_name)
    if os.path.exists(storage_path):
        os.remove(storage_path)

    return "", 204


@bp.route("/<int:id>/serve")
@jwt_required()
def serve_file(id):
    file_obj = db.session.get(File, id) or abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        file_obj.storage_name,
        mimetype=file_obj.type,
    )
