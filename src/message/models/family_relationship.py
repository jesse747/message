from datetime import datetime, timezone

from ..extensions import db

VALID_RELATIONSHIPS = frozenset({"parent", "child", "sibling", "spouse"})


class FamilyRelationship(db.Model):
    __tablename__ = "family_relationships"

    id = db.Column(db.Integer, primary_key=True)
    person_1_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    person_2_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    relationship_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    person_1 = db.relationship("Person", foreign_keys=[person_1_id], back_populates="relationships_as_1")
    person_2 = db.relationship("Person", foreign_keys=[person_2_id], back_populates="relationships_as_2")

    def __repr__(self):
        return f"<FamilyRelationship {self.person_1_id} {self.relationship_type} {self.person_2_id}>"
