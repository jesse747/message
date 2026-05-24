from datetime import datetime, timezone

from ..extensions import db


class GroupMember(db.Model):
    __tablename__ = "group_members"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    role = db.Column(db.String(10), default="member")
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    group = db.relationship("Group", back_populates="members")
    person = db.relationship("Person")

    __table_args__ = (db.UniqueConstraint("group_id", "person_id"),)

    def __repr__(self):
        return f"<GroupMember group={self.group_id} person={self.person_id} role={self.role}>"
