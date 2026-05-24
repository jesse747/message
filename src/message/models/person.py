from datetime import datetime, timezone

from ..extensions import db


class Person(db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email_personal = db.Column(db.String(120), nullable=True)
    email_work = db.Column(db.String(120), nullable=True)
    phone_mobile = db.Column(db.String(30), nullable=True)
    phone_home = db.Column(db.String(30), nullable=True)
    phone_work = db.Column(db.String(30), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(30), nullable=True)

    membership_status = db.Column(
        db.String(20), default="member"
    )
    membership_start_date = db.Column(db.Date, nullable=True)
    membership_type = db.Column(db.String(20), nullable=True)
    membership_number = db.Column(db.String(50), unique=True, nullable=True)
    date_joined = db.Column(db.Date, nullable=True)
    baptism_date = db.Column(db.Date, nullable=True)
    baptism_location = db.Column(db.String(100), nullable=True)
    transferred_from = db.Column(db.String(100), nullable=True)
    membership_notes = db.Column(db.Text, nullable=True)

    date_of_birth = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=True)
    photo_file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="person", uselist=False, foreign_keys=[user_id])
    family = db.relationship("Family", foreign_keys=[family_id], back_populates="members")
    photo = db.relationship("File", foreign_keys=[photo_file_id], uselist=False)
    teams = db.relationship("PersonTeam", back_populates="person", cascade="all, delete-orphan")
    relationships_as_1 = db.relationship(
        "FamilyRelationship",
        foreign_keys="FamilyRelationship.person_1_id",
        back_populates="person_1",
        cascade="all, delete-orphan",
    )
    relationships_as_2 = db.relationship(
        "FamilyRelationship",
        foreign_keys="FamilyRelationship.person_2_id",
        back_populates="person_2",
        cascade="all, delete-orphan",
    )
    flock_memberships = db.relationship("FlockMember", back_populates="person", cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self):
        return f"<Person {self.full_name}>"
