from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, validate, validates_schema
from marshmallow import ValidationError as MarshmallowError

from ...authz import require_capability
from ...extensions import db
from ...models import FamilyRelationship, Person
from ...models.family_relationship import VALID_RELATIONSHIPS

bp = Blueprint("relationships", __name__)


class RelationshipSchema(Schema):
    person_1_id = fields.Integer(required=True)
    person_2_id = fields.Integer(required=True)
    relationship_type = fields.String(
        required=True, validate=validate.OneOf(sorted(VALID_RELATIONSHIPS))
    )

    @validates_schema
    def check_not_self(self, data, **_kwargs):
        if data["person_1_id"] == data["person_2_id"]:
            raise MarshmallowError(
                "Cannot create a relationship with yourself",
                field_name="person_2_id",
            )


relationship_schema = RelationshipSchema()


@bp.route("")
@jwt_required()
def list_relationships():
    person_id = request.args.get("person_id", type=int)
    query = FamilyRelationship.query
    if person_id:
        db.session.get(Person, person_id) or abort(404)
        query = query.filter(
            (FamilyRelationship.person_1_id == person_id)
            | (FamilyRelationship.person_2_id == person_id)
        )
    relationships = query.order_by(FamilyRelationship.created_at.desc()).all()
    return {
        "data": [
            {
                "id": r.id,
                "person_1_id": r.person_1_id,
                "person_2_id": r.person_2_id,
                "relationship_type": r.relationship_type,
            }
            for r in relationships
        ]
    }, 200


@bp.route("", methods=["POST"])
@jwt_required()
@require_capability("edit_directory")
def create_relationship():
    try:
        data = relationship_schema.load(request.json)
    except MarshmallowError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    db.session.get(Person, data["person_1_id"]) or abort(404)
    db.session.get(Person, data["person_2_id"]) or abort(404)

    existing = FamilyRelationship.query.filter(
        (
            (FamilyRelationship.person_1_id == data["person_1_id"])
            & (FamilyRelationship.person_2_id == data["person_2_id"])
        )
        | (
            (FamilyRelationship.person_1_id == data["person_2_id"])
            & (FamilyRelationship.person_2_id == data["person_1_id"])
        )
    ).first()
    if existing:
        return {"error": {"code": "CONFLICT", "message": "Relationship already exists"}}, 409

    rel = FamilyRelationship(**data)
    db.session.add(rel)
    db.session.commit()
    return {
        "data": {
            "id": rel.id,
            "person_1_id": rel.person_1_id,
            "person_2_id": rel.person_2_id,
            "relationship_type": rel.relationship_type,
        }
    }, 201


@bp.route("/<int:id>")
@jwt_required()
def get_relationship(id):
    rel = db.session.get(FamilyRelationship, id) or abort(404)
    return {
        "data": {
            "id": rel.id,
            "person_1_id": rel.person_1_id,
            "person_2_id": rel.person_2_id,
            "relationship_type": rel.relationship_type,
        }
    }, 200


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@require_capability("edit_directory")
def delete_relationship(id):
    rel = db.session.get(FamilyRelationship, id) or abort(404)
    db.session.delete(rel)
    db.session.commit()
    return "", 204
