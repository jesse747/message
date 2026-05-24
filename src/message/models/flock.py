from datetime import datetime, timezone

from ..extensions import db


class Flock(db.Model):
    __tablename__ = "flocks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    members = db.relationship("FlockMember", back_populates="flock", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Flock {self.name}>"
