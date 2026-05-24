from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func

from ..extensions import db


class DutyGroup(db.Model):
    __tablename__ = "duty_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    time = db.Column(db.Time, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    duties = db.relationship("Duty", back_populates="duty_group", cascade="all, delete-orphan")
    memberships = db.relationship(
        "DutyGroupMembership", back_populates="duty_group", cascade="all, delete-orphan"
    )
    posts = db.relationship(
        "Post",
        foreign_keys="Post.duty_group_id",
        back_populates="duty_group",
        cascade="all, delete-orphan",
    )

    def generate_assignments(self, from_date, to_date):
        from .duty_assignment import DutyAssignment
        from .duty_group_membership import DutyGroupMembership

        duties = sorted(
            [d for d in self.duties if d.is_active],
            key=lambda d: d.sort_order,
        )
        if not duties:
            return [], []

        current = from_date
        created = []
        gaps = []
        last_seen = {}

        while current <= to_date:
            if current.weekday() != self.day_of_week:
                current += timedelta(days=1)
                continue

            unfilled = [d for d in duties]
            existing = DutyAssignment.query.filter(
                DutyAssignment.duty_id.in_([d.id for d in duties]),
                DutyAssignment.date == current,
            ).all()

            existing_duty_ids = {a.duty_id for a in existing}
            busy_person_ids = {a.person_id for a in existing}
            unfilled = [d for d in unfilled if d.id not in existing_duty_ids]

            memberships = DutyGroupMembership.query.filter_by(duty_group_id=self.id).filter(
                DutyGroupMembership.date_from <= current,
                (DutyGroupMembership.date_to.is_(None)) | (DutyGroupMembership.date_to >= current),
            ).all()
            available = [
                m.person_id for m in memberships
                if m.person_id not in busy_person_ids
            ]

            if not unfilled:
                current += timedelta(days=1)
                continue

            if not available:
                gaps.append({
                    "date": str(current),
                    "unfilled_duties": [d.name for d in unfilled],
                })
                current += timedelta(days=1)
                continue

            last_assignments = dict(db.session.query(
                DutyAssignment.person_id, func.max(DutyAssignment.date)
            ).filter(
                DutyAssignment.person_id.in_(available),
                DutyAssignment.duty_id.in_([d.id for d in duties]),
            ).group_by(DutyAssignment.person_id).all())

            for pid in available:
                if pid not in last_seen:
                    last_seen[pid] = last_assignments.get(pid, date.min)

            sorted_people = sorted(available, key=lambda pid: last_seen.get(pid, date.min))

            for i, duty in enumerate(unfilled):
                if i >= len(sorted_people):
                    gaps.append({
                        "date": str(current),
                        "unfilled_duties": [d.name for d in unfilled[i:]],
                    })
                    break
                person_id = sorted_people[i]
                created.append(DutyAssignment(
                    duty_id=duty.id,
                    person_id=person_id,
                    date=current,
                ))
                last_seen[person_id] = current

            current += timedelta(days=1)

        return created, gaps

    def __repr__(self):
        return f"<DutyGroup {self.name}>"
