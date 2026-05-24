from datetime import UTC, datetime

from ..extensions import db


class MeetingInstance(db.Model):
    __tablename__ = "meeting_instances"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    cancelled = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    cancellation_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    meeting = db.relationship("Meeting", back_populates="instances")
    files = db.relationship("File", back_populates="meeting_instance", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MeetingInstance {self.meeting.name} {self.date}>"
