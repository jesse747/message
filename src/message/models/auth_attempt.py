from datetime import datetime, timezone

from ..extensions import db


class AuthAttempt(db.Model):
    __tablename__ = "auth_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username_attempted = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(500), nullable=True)
    outcome = db.Column(db.String(10), nullable=False)
    failure_reason = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AuthAttempt {self.username_attempted} {self.outcome}>"
