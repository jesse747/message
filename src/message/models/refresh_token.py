from datetime import datetime, timezone

from ..extensions import db


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="refresh_tokens")

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    @property
    def is_expired(self):
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires

    @property
    def is_valid(self):
        return not self.is_revoked and not self.is_expired

    def revoke(self):
        self.revoked_at = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<RefreshToken user={self.user_id}>"
