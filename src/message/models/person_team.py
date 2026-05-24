from datetime import UTC, datetime

from ..extensions import db


class PersonTeam(db.Model):
    __tablename__ = "person_teams"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    role = db.Column(db.String(50), nullable=True)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    person = db.relationship("Person", back_populates="teams")
    team = db.relationship("Team", back_populates="persons")

    __table_args__ = (db.UniqueConstraint("person_id", "team_id"),)

    def __repr__(self):
        return f"<PersonTeam person={self.person_id} team={self.team_id}>"
