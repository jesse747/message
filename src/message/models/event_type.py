from datetime import UTC, datetime

from ..extensions import db


class EventType(db.Model):
    __tablename__ = "event_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    events = db.relationship(
        "PersonEvent", back_populates="event_type", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<EventType {self.name}>"
