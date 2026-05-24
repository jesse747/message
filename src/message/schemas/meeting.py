from marshmallow import fields, validate

from ..extensions import ma
from ..models import Meeting


class MeetingSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Meeting
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at"]

    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    day_of_week = fields.Integer(required=True, validate=validate.Range(min=0, max=6))
    frequency = fields.String(validate=validate.OneOf(["weekly", "fortnightly", "monthly"]))
