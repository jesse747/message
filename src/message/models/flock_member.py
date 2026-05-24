from datetime import UTC, datetime

from ..extensions import db


class FlockMember(db.Model):
    __tablename__ = "flock_members"

    id = db.Column(db.Integer, primary_key=True)
    flock_id = db.Column(db.Integer, db.ForeignKey("flocks.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), unique=True, nullable=False)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    flock = db.relationship("Flock", back_populates="members")
    person = db.relationship("Person", back_populates="flock_memberships")

    __table_args__ = (db.UniqueConstraint("flock_id", "person_id"),)

    def __repr__(self):
        return f"<FlockMember flock={self.flock_id} person={self.person_id}>"
