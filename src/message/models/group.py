from datetime import UTC, datetime

from ..extensions import db


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    creator = db.relationship("User", foreign_keys=[created_by])

    members = db.relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    posts = db.relationship(
        "Post",
        foreign_keys="Post.group_id",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    files = db.relationship(
        "File",
        foreign_keys="File.group_id",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    meetings = db.relationship(
        "Meeting",
        foreign_keys="Meeting.group_id",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Group {self.name}>"
