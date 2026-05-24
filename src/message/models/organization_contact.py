from datetime import datetime, timezone

from ..extensions import db


class OrganizationContact(db.Model):
    __tablename__ = "organization_contacts"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(
        db.Integer, db.ForeignKey("persons.id"), nullable=False, unique=True
    )
    role = db.Column(db.String(50), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    person = db.relationship("Person")

    def __repr__(self):
        return f"<OrganizationContact person={self.person_id} role={self.role}>"
