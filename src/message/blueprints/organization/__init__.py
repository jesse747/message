from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, validate
from marshmallow import ValidationError as MarshmallowError

from ...authz import require_capability
from ...extensions import db
from ...models import Organization, OrganizationContact, Person

bp = Blueprint("organization", __name__)


class ContactSchema(Schema):
    person_id = fields.Integer(required=True)
    role = fields.String(allow_none=True, validate=validate.Length(max=50))


contact_schema = ContactSchema()


def _contact_data(contact):
    return {
        "person_id": contact.person_id,
        "first_name": contact.person.first_name if contact.person else None,
        "last_name": contact.person.last_name if contact.person else None,
        "role": contact.role,
    }


def _org_data(org):
    contacts = (
        OrganizationContact.query
        .order_by(OrganizationContact.sort_order)
        .all()
    )
    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "email": org.email,
        "phone": org.phone,
        "address": org.address,
        "website": org.website,
        "contacts": [_contact_data(c) for c in contacts],
    }


@bp.route("")
def get_organization():
    contacts = (
        OrganizationContact.query
        .order_by(OrganizationContact.sort_order)
        .all()
    )
    org = Organization.query.first()
    if not org:
        return {
            "data": {
                "id": None, "name": None, "description": None,
                "email": None, "phone": None, "address": None,
                "website": None,
                "contacts": [_contact_data(c) for c in contacts],
            }
        }, 200
    return {"data": _org_data(org)}, 200


@bp.route("", methods=["PATCH"])
@jwt_required()
@require_capability("manage_organization")
def update_organization():
    data = request.get_json(silent=True) or {}
    org = Organization.query.first()
    if not org:
        org = Organization(
            name=data.get("name", ""),
            description=data.get("description"),
            email=data.get("email"),
            phone=data.get("phone"),
            address=data.get("address"),
            website=data.get("website"),
        )
        db.session.add(org)
    else:
        for field in ("name", "description", "email", "phone", "address", "website"):
            if field in data:
                setattr(org, field, data[field])
    db.session.commit()
    return {"data": _org_data(org)}, 200


@bp.route("/contacts")
@jwt_required()
def list_contacts():
    contacts = (
        OrganizationContact.query
        .order_by(OrganizationContact.sort_order)
        .all()
    )
    return {"data": [_contact_data(c) for c in contacts]}, 200


@bp.route("/contacts", methods=["POST"])
@jwt_required()
@require_capability("manage_organization")
def add_contact():
    try:
        data = contact_schema.load(request.get_json())
    except MarshmallowError as e:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": e.messages,
            }
        }, 422

    person = db.session.get(Person, data["person_id"])
    if not person:
        return {"error": {"code": "NOT_FOUND", "message": "Person not found"}}, 404

    existing = OrganizationContact.query.filter_by(person_id=data["person_id"]).first()
    if existing:
        return {
            "error": {
                "code": "CONFLICT",
                "message": "Person is already a designated contact",
            }
        }, 409

    contact = OrganizationContact(
        person_id=data["person_id"],
        role=data.get("role"),
    )
    db.session.add(contact)
    db.session.commit()

    return {"data": _contact_data(contact)}, 201


@bp.route("/contacts/<int:person_id>", methods=["PATCH"])
@jwt_required()
@require_capability("manage_organization")
def update_contact(person_id):
    contact = OrganizationContact.query.filter_by(person_id=person_id).first()
    if not contact:
        return {"error": {"code": "NOT_FOUND", "message": "Contact not found"}}, 404

    data = request.get_json(silent=True) or {}
    if "role" in data:
        contact.role = data["role"]
    db.session.commit()

    return {"data": _contact_data(contact)}, 200


@bp.route("/contacts/<int:person_id>", methods=["DELETE"])
@jwt_required()
@require_capability("manage_organization")
def delete_contact(person_id):
    contact = OrganizationContact.query.filter_by(person_id=person_id).first()
    if not contact:
        return {"error": {"code": "NOT_FOUND", "message": "Contact not found"}}, 404

    db.session.delete(contact)
    db.session.commit()
    return "", 204
