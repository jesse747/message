from datetime import UTC, datetime

from ..extensions import db

CAPABILITY_MAP = {
    "edit_directory": "persons.manage",
    "manage_announcements": "bulletin.manage",
    "manage_teams": "teams.manage",
    "manage_groups": "groups.manage",
    "manage_rosters": "duties.manage",
    "manage_flocks": "flocks.manage",
    "manage_events": "events.manage",
    "manage_organization": "organization.manage",
    "manage_users": "users.manage",
    "manage_files": "files.manage",
}

INTERNAL_TO_CAPABILITY = {v: k for k, v in CAPABILITY_MAP.items()}


class UserPermission(db.Model):
    __tablename__ = "user_permissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    permission = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    user = db.relationship("User", back_populates="permissions")

    __table_args__ = (db.UniqueConstraint("user_id", "permission"),)

    def matches_capability(self, capability):
        internal = CAPABILITY_MAP.get(capability)
        return self.permission == internal

    def __repr__(self):
        return f"<UserPermission {self.permission}>"
