from datetime import UTC, datetime

from ..extensions import db


class Family(db.Model):
    __tablename__ = "families"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    head_person_id = db.Column(
        db.Integer, db.ForeignKey("persons.id"), unique=True, nullable=True
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    photo_file_id = db.Column(
        db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    photo = db.relationship("File", foreign_keys=[photo_file_id], uselist=False)

    head_person = db.relationship(
        "Person",
        foreign_keys=[head_person_id],
        uselist=False,
        post_update=True,
    )
    members = db.relationship(
        "Person", foreign_keys="Person.family_id", back_populates="family"
    )

    def __repr__(self):
        return f"<Family {self.name or self.id}>"
