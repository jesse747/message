from datetime import datetime, timezone

from ..extensions import db


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    team_admin_id = db.Column(db.Integer, db.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    parent = db.relationship("Team", remote_side="Team.id", back_populates="children")
    children = db.relationship("Team", back_populates="parent", cascade="all, delete-orphan")

    team_admin = db.relationship("Person", foreign_keys=[team_admin_id], uselist=False)
    persons = db.relationship("PersonTeam", back_populates="team", cascade="all, delete-orphan")
    posts = db.relationship("Post", foreign_keys="Post.team_id", back_populates="team", cascade="all, delete-orphan")
    files = db.relationship("File", foreign_keys="File.team_id", back_populates="team", cascade="all, delete-orphan")
    meetings = db.relationship(
        "Meeting", foreign_keys="Meeting.team_id", back_populates="team", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Team {self.name}>"
