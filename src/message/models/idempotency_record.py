from datetime import datetime, timezone, timedelta

from ..extensions import db


class IdempotencyRecord(db.Model):
    __tablename__ = "idempotency_records"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    request_method = db.Column(db.String(10), nullable=False)
    request_path = db.Column(db.String(200), nullable=False)
    request_sha256 = db.Column(db.String(64), nullable=False)
    response_status = db.Column(db.Integer, nullable=False)
    response_body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
    )

    def __repr__(self):
        return f"<IdempotencyRecord {self.key}>"
