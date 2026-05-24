from marshmallow import fields, validate

from ..extensions import ma
from ..models import Person


class PersonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Person
        load_instance = False
        include_fk = True
        exclude = ["created_by", "created_at", "updated_at"]

    first_name = fields.String(required=True, validate=validate.Length(min=1, max=80))
    last_name = fields.String(required=True, validate=validate.Length(min=1, max=80))
    email_personal = fields.Email(allow_none=True)
    email_work = fields.Email(allow_none=True)
    membership_status = fields.String(
        validate=validate.OneOf(["member", "visitor", "inactive", "former"])
    )
    membership_type = fields.String(
        validate=validate.OneOf(["regular", "associate", "honorary"]),
        allow_none=True,
    )
    date_of_birth = fields.Date(allow_none=True)
