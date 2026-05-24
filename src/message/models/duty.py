from datetime import UTC, datetime

from ..extensions import db


class Duty(db.Model):
    __tablename__ = "duties"

    id = db.Column(db.Integer, primary_key=True)
    duty_group_id = db.Column(db.Integer, db.ForeignKey("duty_groups.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    duty_group = db.relationship("DutyGroup", back_populates="duties")
    assignments = db.relationship(
        "DutyAssignment", back_populates="duty", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Duty {self.name}>"
