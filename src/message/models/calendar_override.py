from datetime import datetime, timezone

from ..extensions import db


class CalendarOverride(db.Model):
    __tablename__ = "calendar_overrides"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_cancelled = db.Column(db.Boolean, default=False)
    override_title = db.Column(db.String(200), nullable=True)
    override_location = db.Column(db.String(200), nullable=True)
    override_color = db.Column(db.String(7), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    event = db.relationship("CalendarEvent", back_populates="overrides")

    __table_args__ = (db.UniqueConstraint("event_id", "date"),)

    def __repr__(self):
        return f"<CalendarOverride event={self.event_id} date={self.date}>"
