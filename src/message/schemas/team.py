from marshmallow import fields, validate

from ..extensions import ma
from ..models import Team


class TeamSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Team
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at"]

    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    parent_id = fields.Integer(allow_none=True, load_default=None)
    team_admin_id = fields.Integer(allow_none=True, load_default=None)


class TeamUpdateSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Team
        load_instance = False
        partial = True

    name = fields.String(validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True)
    parent_id = fields.Integer(allow_none=True)
    team_admin_id = fields.Integer(allow_none=True)
