from datetime import UTC, datetime

from ..extensions import db


class PersonEvent(db.Model):
    __tablename__ = "person_events"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    event_type_id = db.Column(
        db.Integer, db.ForeignKey("event_types.id"), nullable=False
    )
    event_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    file_id = db.Column(
        db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    person = db.relationship("Person", back_populates="events")
    event_type = db.relationship("EventType", back_populates="events")
    file = db.relationship("File", foreign_keys=[file_id], uselist=False)

    @property
    def file_url(self):
        if self.file_id:
            return f"/api/v1/files/{self.file_id}/serve"
        return None

    def __repr__(self):
        return (
            f"<PersonEvent"
            f" {self.event_type.name if self.event_type else None}"
            f" person={self.person_id}>"
        )
