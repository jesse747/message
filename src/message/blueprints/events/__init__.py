from flask import Blueprint, abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ...authz import require_capability
from ...extensions import db
from ...models import CalendarEvent, CalendarOverride
from ...schemas.event import CalendarEventSchema

bp = Blueprint("events", __name__)
event_schema = CalendarEventSchema()


def _event_data(e):
    return {
        "id": e.id,
        "title": e.title,
        "description": e.description,
        "team_id": e.team_id,
        "group_id": e.group_id,
        "location": e.location,
        "color": e.color,
        "is_all_day": e.is_all_day,
        "start_time": str(e.start_time) if e.start_time else None,
        "end_time": str(e.end_time) if e.end_time else None,
        "frequency": e.frequency,
        "first_date": str(e.first_date) if e.first_date else None,
        "last_date": str(e.last_date) if e.last_date else None,
    }


@bp.route("")
@jwt_required()
def list_events():
    """List calendar events with optional search.
    ---
    tags:
      - Events
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
        description: Paginated list of calendar events
    """
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = CalendarEvent.query
    if q:
        query = query.filter(CalendarEvent.title.ilike(f"%{q}%"))

    total = query.count()
    events = (
        query.order_by(CalendarEvent.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "data": [_event_data(e) for e in events],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("manage_events")
def create_event():
    try:
        data = event_schema.load(request.json)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    event = CalendarEvent(**data, created_by=int(get_jwt_identity()))
    db.session.add(event)
    db.session.commit()
    return {"data": _event_data(event)}, 201


@bp.route("/<int:id>")
@jwt_required()
def get_event(id):
    event = db.session.get(CalendarEvent, id) or abort(404)
    from ...models import CalendarOverride

    overrides = CalendarOverride.query.filter_by(event_id=id).all()
    return {
        "data": {
            **_event_data(event),
            "overrides": [
                {
                    "id": o.id,
                    "date": str(o.date),
                    "is_cancelled": o.is_cancelled,
                    "override_title": o.override_title,
                    "override_location": o.override_location,
                    "notes": o.notes,
                }
                for o in overrides
            ],
        }
    }, 200


@bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_events")
def update_event(id):
    event = db.session.get(CalendarEvent, id) or abort(404)
    try:
        data = event_schema.load(request.json, partial=True)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    for key, val in data.items():
        setattr(event, key, val)
    db.session.commit()
    return {"data": _event_data(event)}, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_events")
def delete_event(id):
    event = db.session.get(CalendarEvent, id) or abort(404)
    db.session.delete(event)
    db.session.commit()
    return "", 204


@bp.route("/<int:event_id>/overrides")
@jwt_required()
def list_overrides(event_id):
    db.session.get(CalendarEvent, event_id) or abort(404)
    from ...models import CalendarOverride

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    query = CalendarOverride.query.filter_by(event_id=event_id)
    if date_from:
        query = query.filter(CalendarOverride.date >= date_from)
    if date_to:
        query = query.filter(CalendarOverride.date <= date_to)

    overrides = query.order_by(CalendarOverride.date).all()
    return {
        "data": [
            {
                "id": o.id,
                "date": str(o.date),
                "is_cancelled": o.is_cancelled,
                "override_title": o.override_title,
                "override_location": o.override_location,
                "notes": o.notes,
            }
            for o in overrides
        ]
    }, 200


@bp.route("/<int:event_id>/overrides", methods=["POST"])
@jwt_required()
@require_capability("manage_events")
def create_override(event_id):
    db.session.get(CalendarEvent, event_id) or abort(404)
    data = request.get_json(silent=True) or {}
    from ...models import CalendarOverride
    from ...schemas.event import CalendarOverrideSchema

    try:
        override_data = CalendarOverrideSchema().load(data)
    except ValidationError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    override = CalendarOverride(**override_data, event_id=event_id)
    db.session.add(override)
    db.session.commit()
    return {
        "data": {
            "id": override.id,
            "event_id": event_id,
            "date": str(override.date),
            "is_cancelled": override.is_cancelled,
        }
    }, 201


@bp.route("/<int:id>/<date>")
@jwt_required()
def get_event_occurrence(id, date):
    event = db.session.get(CalendarEvent, id) or abort(404)

    try:
        from datetime import datetime as dt
        occurrence_date = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {
            "error": {"code": "BAD_REQUEST", "message": "Invalid date format. Use YYYY-MM-DD"}
        }, 400

    from ...blueprints.calendar import _resolve_event_dates

    resolved_dates = _resolve_event_dates(event, occurrence_date, occurrence_date)
    if not resolved_dates:
        return {
            "error": {
                "code": "NOT_FOUND",
                "message": "No occurrence of this event on that date",
            }
        }, 404

    override = CalendarOverride.query.filter_by(
        event_id=event.id, date=occurrence_date
    ).first()

    return {
        "data": {
            "event": {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "team_id": event.team_id,
                "group_id": event.group_id,
                "location": event.location,
                "color": event.color,
                "is_all_day": event.is_all_day,
                "start_time": str(event.start_time) if event.start_time else None,
                "end_time": str(event.end_time) if event.end_time else None,
                "frequency": event.frequency,
                "first_date": str(event.first_date) if event.first_date else None,
                "last_date": str(event.last_date) if event.last_date else None,
            },
            "occurrence_date": str(occurrence_date),
            "resolved": {
                "title": (
                    override.override_title
                    if (override and override.override_title)
                    else event.title
                ),
                "location": (
                    override.override_location
                    if (override and override.override_location)
                    else event.location
                ),
                "color": (
                    override.override_color
                    if (override and override.override_color)
                    else event.color
                ),
                "time": str(event.start_time) if event.start_time else None,
                "end_time": str(event.end_time) if event.end_time else None,
                "is_cancelled": override.is_cancelled if override else False,
                "has_override": override is not None,
                "override_notes": override.notes if override else None,
            },
        }
    }, 200
