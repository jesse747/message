from datetime import UTC, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    avatar = db.Column(db.String(200), nullable=True)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    person = db.relationship(
        "Person",
        uselist=False,
        back_populates="user",
        foreign_keys="Person.user_id",
    )
    permissions = db.relationship(
        "UserPermission", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = db.relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    @property
    def identity(self):
        return self.id

    def has_capability(self, capability):
        if self.is_super_admin:
            return True
        return any(p.matches_capability(capability) for p in self.permissions)

    def __repr__(self):
        return f"<User {self.username}>"
