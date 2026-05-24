from marshmallow import fields, validate

from ..extensions import ma
from ..models import Post


class PostSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Post
        load_instance = False
        include_fk = True
        exclude = ["author_id", "created_at", "updated_at"]

    content = fields.String(required=True, validate=validate.Length(min=1))
    show_on_bulletin = fields.Boolean(load_default=False)


class PostUpdateSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Post
        load_instance = False
        partial = True

    content = fields.String(validate=validate.Length(min=1))
    is_pinned = fields.Boolean()
    show_on_bulletin = fields.Boolean()
    expires_at = fields.DateTime(allow_none=True)
