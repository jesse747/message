from datetime import datetime, timezone

from ..extensions import db


class DutyAssignment(db.Model):
    __tablename__ = "duty_assignments"

    id = db.Column(db.Integer, primary_key=True)
    duty_id = db.Column(db.Integer, db.ForeignKey("duties.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    duty = db.relationship("Duty", back_populates="assignments")
    person = db.relationship("Person")

    def __repr__(self):
        return f"<DutyAssignment duty={self.duty_id} person={self.person_id} date={self.date}>"
