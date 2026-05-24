from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from ...authz import require_capability
from ...extensions import db
from ...models import EventType
from ...schemas.event_type import EventTypeSchema, EventTypeUpdateSchema

bp = Blueprint("event_types", __name__)
event_type_schema = EventTypeSchema()
event_type_update_schema = EventTypeUpdateSchema()


@bp.route("")
@jwt_required()
def list_event_types():
    """List event types. Returns active types by default.
    ---
    tags:
      - Event Types
    security:
      - Bearer: []
    parameters:
      - name: all
        in: query
        schema: {type: boolean}
        description: Include inactive types
      - name: page
        in: query
        schema: {type: integer, default: 1}
      - name: limit
        in: query
        schema: {type: integer, default: 20, maximum: 100}
    responses:
      200:
        description: Paginated list of event types
    """
    show_all = request.args.get("all", "").lower() == "true"
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = EventType.query
    if not show_all:
        query = query.filter_by(is_active=True)
    query = query.order_by(EventType.sort_order, EventType.name)

    total = query.count()
    event_types = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [
            {
                "id": et.id,
                "name": et.name,
                "description": et.description,
                "is_active": et.is_active,
                "sort_order": et.sort_order,
            }
            for et in event_types
        ],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("/<int:id>")
@jwt_required()
def get_event_type(id):
    """Get a single event type by ID.
    ---
    tags:
      - Event Types
    security:
      - Bearer: []
    parameters:
      - name: id
        in: path
        required: true
        schema: {type: integer}
    responses:
      200:
        description: Event type details
      404:
        description: Event type not found
    """
    event_type = db.session.get(EventType, id) or abort(404)
    return {
        "data": {
            "id": event_type.id,
            "name": event_type.name,
            "description": event_type.description,
            "is_active": event_type.is_active,
            "sort_order": event_type.sort_order,
        }
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("edit_directory")
def create_event_type():
    try:
        data = event_type_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    if EventType.query.filter_by(name=data["name"]).first():
        return {
            "error": {"code": "CONFLICT", "message": "Event type name already exists"}
        }, 409

    event_type = EventType(**data)
    db.session.add(event_type)
    db.session.commit()
    return {
        "data": {
            "id": event_type.id,
            "name": event_type.name,
            "description": event_type.description,
            "is_active": event_type.is_active,
            "sort_order": event_type.sort_order,
        }
    }, 201


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_capability("edit_directory")
def update_event_type(id):
    event_type = db.session.get(EventType, id) or abort(404)

    try:
        data = event_type_update_schema.load(request.json)
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
        and data["name"] != event_type.name
        and EventType.query.filter_by(name=data["name"]).first()
    ):
        return {
            "error": {
                "code": "CONFLICT",
                "message": "Event type name already exists",
            }
        }, 409

    for key, val in data.items():
        setattr(event_type, key, val)
    db.session.commit()
    return {
        "data": {
            "id": event_type.id,
            "name": event_type.name,
            "description": event_type.description,
            "is_active": event_type.is_active,
            "sort_order": event_type.sort_order,
        }
    }, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("edit_directory")
def delete_event_type(id):
    event_type = db.session.get(EventType, id) or abort(404)
    event_type.is_active = False
    db.session.commit()
    return "", 204
