from marshmallow import fields, validate

from ..extensions import ma
from ..models import Group, GroupMember


class GroupSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Group
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at", "created_by"]

    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    is_public = fields.Boolean(load_default=False)


class GroupUpdateSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Group
        load_instance = False
        partial = True

    name = fields.String(validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True)
    is_public = fields.Boolean()


class GroupMemberSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = GroupMember
        load_instance = False
        include_fk = True
        exclude = ["joined_at", "group_id"]


class GroupMemberUpdateSchema(ma.SQLAlchemySchema):
    class Meta:
        model = GroupMember
        load_instance = False
        partial = True

    role = fields.String(required=True, validate=validate.OneOf(["admin", "member"]))
