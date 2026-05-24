from marshmallow import fields, validate

from ..extensions import ma
from ..models import PersonEvent


class PersonEventSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PersonEvent
        load_instance = False
        include_fk = True
        exclude = ["person_id", "file_id", "created_by", "created_at", "updated_at"]

    event_type_id = fields.Integer(required=True)
    event_date = fields.Date(required=True)
    location = fields.String(allow_none=True, validate=validate.Length(max=100))
    notes = fields.String(allow_none=True)


class PersonEventUpdateSchema(ma.SQLAlchemySchema):
    class Meta:
        model = PersonEvent
        load_instance = False
        partial = True

    event_type_id = fields.Integer()
    event_date = fields.Date()
    location = fields.String(allow_none=True, validate=validate.Length(max=100))
    notes = fields.String(allow_none=True)
