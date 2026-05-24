import secrets
from datetime import UTC, datetime, timedelta

from src.message.models import InviteToken, Person, User


def create_user(db, username, email, password="password123", first_name="Test", last_name="User", is_super_admin=False):
    user = User(username=username, email=email, display_name=first_name)
    user.set_password(password)
    user.is_super_admin = is_super_admin
    db.session.add(user)
    db.session.flush()
    person = Person(
        first_name=first_name,
        last_name=last_name,
        email_personal=email,
        user_id=user.id,
        created_by=user.id,
    )
    db.session.add(person)
    db.session.commit()
    return user


def register_user_via_invite(client, db, username, email, password="password123", first_name="Test", last_name="User"):
    creator = User(username=f"cr_{secrets.token_hex(4)}", email=f"cr_{secrets.token_hex(4)}@test.local", display_name="Creator")
    creator.set_password("x")
    db.session.add(creator)
    db.session.flush()
    person = Person(first_name=first_name, last_name=last_name, email_personal=email, created_by=creator.id)
    db.session.add(person)
    db.session.flush()
    invite = InviteToken(
        code=secrets.token_urlsafe(32),
        person_id=person.id,
        email=email,
        created_by=creator.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.session.add(invite)
    db.session.commit()
    return client.post("/api/v1/auth/users", json={
        "invite_code": invite.code,
        "email": email,
        "username": username,
        "password": password,
    })
