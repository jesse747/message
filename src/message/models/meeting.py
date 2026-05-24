from datetime import datetime, timezone, timedelta, date

from ..extensions import db


class Meeting(db.Model):
    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    time = db.Column(db.Time, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    frequency = db.Column(db.String(20), default="weekly")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    team = db.relationship("Team", back_populates="meetings")
    group = db.relationship("Group", back_populates="meetings")
    instances = db.relationship(
        "MeetingInstance", back_populates="meeting", cascade="all, delete-orphan", order_by="MeetingInstance.date"
    )

    def generate_instances(self, count=12):
        from .meeting_instance import MeetingInstance

        today = date.today()
        current = today - timedelta(days=today.weekday()) + timedelta(days=self.day_of_week)
        if current < today:
            current += timedelta(weeks=1)

        interval_map = {"weekly": 7, "fortnightly": 14, "monthly": 28}
        interval = interval_map.get(self.frequency, 7)

        instances = []
        for i in range(count):
            instances.append(MeetingInstance(
                meeting_id=self.id,
                date=current + timedelta(days=interval * i),
                time=self.time,
                location=self.location,
            ))
        return instances

    def __repr__(self):
        return f"<Meeting {self.name}>"
