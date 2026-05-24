from datetime import datetime, timezone

from ..extensions import db


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    meeting_instance_id = db.Column(db.Integer, db.ForeignKey("meeting_instances.id"), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    author = db.relationship("User")
    team = db.relationship("Team", back_populates="posts")
    group = db.relationship("Group", back_populates="posts")
    meeting_instance = db.relationship("MeetingInstance")
    files = db.relationship("File", foreign_keys="File.post_id", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post {self.id}>"
