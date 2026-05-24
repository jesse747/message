from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from ..extensions import ma
from ..models import DutyGroup, Duty, DutyGroupMembership, DutyAssignment


class SwapChangeSchema(Schema):
    duty_id = fields.Integer(required=True)
    from_person_id = fields.Integer(required=True)
    to_person_id = fields.Integer(required=True)

    @validates_schema
    def validate_not_same(self, data, **kwargs):
        if data["from_person_id"] == data["to_person_id"]:
            raise ValidationError("from_person_id and to_person_id must differ", field_name="to_person_id")


class SwapSchema(Schema):
    date = fields.Date(required=True)
    changes = fields.List(
        fields.Nested(SwapChangeSchema), required=True, validate=validate.Length(min=1)
    )


class AutoAssignSchema(Schema):
    from_date = fields.Date(required=True)
    to_date = fields.Date(required=False)


class DutyGroupSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = DutyGroup
        load_instance = False
        exclude = ["created_at", "updated_at"]

    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    day_of_week = fields.Integer(required=True, validate=validate.Range(min=0, max=6))


class DutySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Duty
        load_instance = False
        include_fk = True
        exclude = ["created_at", "updated_at", "duty_group_id"]

    name = fields.String(required=True, validate=validate.Length(min=1, max=100))


class DutyGroupMembershipSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = DutyGroupMembership
        load_instance = False
        include_fk = True
        exclude = ["created_at", "duty_group_id"]

    date_from = fields.Date(required=True)


class DutyAssignmentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = DutyAssignment
        load_instance = False
        include_fk = True
        exclude = ["created_at", "duty_id"]

    date = fields.Date(required=True)
