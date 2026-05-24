from datetime import datetime, timezone

from ..extensions import db


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    color = db.Column(db.String(7), nullable=True)
    is_all_day = db.Column(db.Boolean, default=False)
    frequency = db.Column(db.String(20), default="none")
    first_date = db.Column(db.Date, nullable=True)
    last_date = db.Column(db.Date, nullable=True)
    fixed_month = db.Column(db.Integer, nullable=True)
    fixed_day = db.Column(db.Integer, nullable=True)
    easter_offset = db.Column(db.Integer, nullable=True)
    nth = db.Column(db.Integer, nullable=True)
    weekday = db.Column(db.Integer, nullable=True)
    nth_month = db.Column(db.Integer, nullable=True)
    target_month = db.Column(db.Integer, nullable=True)
    target_day = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    creator = db.relationship("User")
    overrides = db.relationship("CalendarOverride", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CalendarEvent {self.title}>"
