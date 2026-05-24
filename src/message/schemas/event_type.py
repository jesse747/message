from marshmallow import fields, validate

from ..extensions import ma
from ..models import EventType


class EventTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = EventType
        load_instance = False
        include_fk = True
        exclude = ["created_at"]

    name = fields.String(required=True, validate=validate.Length(min=1, max=50))


class EventTypeUpdateSchema(ma.SQLAlchemySchema):
    class Meta:
        model = EventType
        load_instance = False
        partial = True

    name = fields.String(validate=validate.Length(min=1, max=50))
    description = fields.String(allow_none=True)
    is_active = fields.Boolean()
    sort_order = fields.Integer()
