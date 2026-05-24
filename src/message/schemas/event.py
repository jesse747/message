from marshmallow import fields, validate

from ..extensions import ma
from ..models import CalendarEvent, CalendarOverride


class CalendarEventSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CalendarEvent
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at", "created_by"]

    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    frequency = fields.String(load_default="none", validate=validate.OneOf([
        "none", "fixed", "easter", "nth_weekday", "advent_sunday", "sunday_on_or_before"
    ]))


class CalendarOverrideSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CalendarOverride
        load_instance = False
        include_fk = True
        exclude = ["created_at", "event_id"]
