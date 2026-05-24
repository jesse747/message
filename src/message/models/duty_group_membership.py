from datetime import datetime, timezone

from ..extensions import db


class DutyGroupMembership(db.Model):
    __tablename__ = "duty_group_memberships"

    id = db.Column(db.Integer, primary_key=True)
    duty_group_id = db.Column(db.Integer, db.ForeignKey("duty_groups.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    date_from = db.Column(db.Date, nullable=False)
    date_to = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    duty_group = db.relationship("DutyGroup", back_populates="memberships")
    person = db.relationship("Person")

    __table_args__ = (db.UniqueConstraint("duty_group_id", "person_id", "date_from"),)

    def __repr__(self):
        return f"<DutyGroupMembership group={self.duty_group_id} person={self.person_id}>"
