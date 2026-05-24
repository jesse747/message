from datetime import UTC, datetime

from ..extensions import db


class File(db.Model):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    meeting_instance_id = db.Column(
        db.Integer, db.ForeignKey("meeting_instances.id"), nullable=True
    )
    person_event_id = db.Column(
        db.Integer, db.ForeignKey("person_events.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    storage_name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    uploader = db.relationship("User")
    team = db.relationship("Team", back_populates="files")
    group = db.relationship("Group", back_populates="files")
    post = db.relationship("Post", back_populates="files")
    meeting_instance = db.relationship("MeetingInstance", back_populates="files")
    person_event = db.relationship("PersonEvent", foreign_keys=[person_event_id])

    def __repr__(self):
        return f"<File {self.name}>"
