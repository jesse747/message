from datetime import UTC, datetime

from ..extensions import db


class InviteToken(db.Model):
    __tablename__ = "invite_tokens"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    person = db.relationship("Person")
    creator = db.relationship("User", foreign_keys=[created_by])

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(UTC) > expires

    @property
    def is_valid(self):
        return self.is_active and not self.is_used and not self.is_expired

    def use(self):
        self.used_at = datetime.now(UTC)

    def __repr__(self):
        return f"<InviteToken person={self.person_id}>"
