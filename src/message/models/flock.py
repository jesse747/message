from datetime import UTC, datetime

from ..extensions import db


class Flock(db.Model):
    __tablename__ = "flocks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    shepherd_id = db.Column(
        db.Integer, db.ForeignKey("persons.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    members = db.relationship("FlockMember", back_populates="flock", cascade="all, delete-orphan")
    shepherd = db.relationship("Person", foreign_keys=[shepherd_id], uselist=False)

    def __repr__(self):
        return f"<Flock {self.name}>"
