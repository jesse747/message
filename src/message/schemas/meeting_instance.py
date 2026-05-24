from marshmallow import fields, validate

from ..extensions import ma
from ..models import MeetingInstance


class MeetingInstanceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = MeetingInstance
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at", "meeting_id"]

    date = fields.Date(required=True)
    time = fields.Time(allow_none=True)
    location = fields.String(allow_none=True, validate=validate.Length(max=200))
    notes = fields.String(allow_none=True)
    cancellation_message = fields.String(allow_none=True)


class MeetingInstanceUpdateSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = MeetingInstance
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at", "meeting_id"]

    date = fields.Date(required=False)
    time = fields.Time(allow_none=True)
    location = fields.String(allow_none=True, validate=validate.Length(max=200))
    notes = fields.String(allow_none=True)
    cancelled = fields.Boolean(load_default=False)
    cancellation_message = fields.String(allow_none=True)
