from marshmallow import fields, validate

from ..extensions import ma
from ..models import Flock, FlockMember


class FlockSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Flock
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at", "created_by"]

    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    shepherd_id = fields.Integer(allow_none=True)


class FlockMemberSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FlockMember
        load_instance = False
        include_fk = True
        exclude = ["created_at", "flock_id"]

    person_id = fields.Integer(required=True)
