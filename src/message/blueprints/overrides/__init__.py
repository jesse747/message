from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required

from ...authz import require_capability
from ...extensions import db
from ...models import CalendarOverride

bp = Blueprint("overrides", __name__)


@bp.route("/<int:id>")
@jwt_required()
def get_override(id):
    o = db.session.get(CalendarOverride, id) or abort(404)
    return {
        "data": {
            "id": o.id,
            "event_id": o.event_id,
            "date": str(o.date),
            "is_cancelled": o.is_cancelled,
            "override_title": o.override_title,
            "override_location": o.override_location,
            "notes": o.notes,
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_events")
def update_override(id):
    o = db.session.get(CalendarOverride, id) or abort(404)
    data = request.get_json(silent=True) or {}
    for key in ("is_cancelled", "override_title", "override_location", "notes"):
        if key in data:
            setattr(o, key, data[key])
    db.session.commit()
    return {
        "data": {
            "id": o.id,
            "event_id": o.event_id,
            "date": str(o.date),
            "is_cancelled": o.is_cancelled,
        }
    }, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_events")
def delete_override(id):
    o = db.session.get(CalendarOverride, id) or abort(404)
    db.session.delete(o)
    db.session.commit()
    return "", 204
