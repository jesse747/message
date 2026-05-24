import secrets
from datetime import datetime, timedelta, timezone

from src.message.models import InviteToken, Person, User
from tests.helpers import register_user_via_invite


class TestRegister:
    def test_register_success(self, client, db):
        r = register_user_via_invite(client, db, "newuser", "new@example.com")
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "newuser"

    def test_register_duplicate_username(self, client, db, auth_headers):
        r = register_user_via_invite(client, db, "testuser", "other@example.com")
        assert r.status_code == 409
        assert r.get_json()["error"]["code"] == "CONFLICT"

    def test_register_duplicate_email(self, client, db, auth_headers):
        r = register_user_via_invite(client, db, "other", "test@example.com")
        assert r.status_code == 409

    def test_register_validation_error(self, client, db):
        r = client.post("/api/v1/auth/users", json={"username": "x"})
        assert r.status_code == 422

    def test_register_invalid_invite(self, client, db):
        r = client.post("/api/v1/auth/users", json={
            "invite_code": "nonexistent",
            "email": "x@example.com",
            "username": "test",
            "password": "password123",
        })
        assert r.status_code == 410
        assert r.get_json()["error"]["code"] == "GONE"

    def test_register_expired_invite(self, client, db):
        creator = User(username=f"exp_{secrets.token_hex(4)}", email=f"exp_{secrets.token_hex(4)}@test.local", display_name="Creator")
        creator.set_password("x")
        db.session.add(creator)
        db.session.flush()
        person = Person(first_name="Exp", last_name="ired", email_personal="expired@example.com", created_by=creator.id)
        db.session.add(person)
        db.session.flush()
        invite = InviteToken(
            code=secrets.token_urlsafe(32),
            person_id=person.id,
            email="expired@example.com",
            created_by=creator.id,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.session.add(invite)
        db.session.commit()
        r = client.post("/api/v1/auth/users", json={
            "invite_code": invite.code,
            "email": "expired@example.com",
            "username": "expireduser",
            "password": "password123",
        })
        assert r.status_code == 410

    def test_register_used_invite(self, client, db):
        r = register_user_via_invite(client, db, "useduser", "used@example.com")
        assert r.status_code == 201
        r2 = client.post("/api/v1/auth/users", json={
            "invite_code": r.get_json()["data"]["access_token"],
            "email": "used@example.com",
            "username": "useduser2",
            "password": "password123",
        })
        assert r2.status_code == 410

    def test_register_email_mismatch(self, client, db):
        creator = User(username=f"mm_{secrets.token_hex(4)}", email=f"mm_{secrets.token_hex(4)}@test.local", display_name="Creator")
        creator.set_password("x")
        db.session.add(creator)
        db.session.flush()
        person = Person(first_name="Mismatch", last_name="Test", email_personal="correct@example.com", created_by=creator.id)
        db.session.add(person)
        db.session.flush()
        invite = InviteToken(
            code=secrets.token_urlsafe(32),
            person_id=person.id,
            email="correct@example.com",
            created_by=creator.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.session.add(invite)
        db.session.commit()
        r = client.post("/api/v1/auth/users", json={
            "invite_code": invite.code,
            "email": "wrong@example.com",
            "username": "mismatch",
            "password": "password123",
        })
        assert r.status_code == 422


class TestLogin:
    def test_login_success(self, client, db, auth_headers):
        r = client.post("/api/v1/auth/sessions", json={"username": "testuser", "password": "password123"})
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "access_token" in data

    def test_login_by_email(self, client, db):
        register_user_via_invite(client, db, "user2", "user2@example.com")
        r = client.post("/api/v1/auth/sessions", json={"username": "user2@example.com", "password": "password123"})
        assert r.status_code == 200

    def test_login_bad_password(self, client, db):
        r = client.post("/api/v1/auth/sessions", json={"username": "testuser", "password": "wrong"})
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        r = client.post("/api/v1/auth/sessions", json={"username": "nobody", "password": "x"})
        assert r.status_code == 401

    def test_login_validation_error(self, client, db):
        r = client.post("/api/v1/auth/sessions", json={})
        assert r.status_code == 422


class TestMe:
    def test_me_success(self, client, db, auth_headers):
        r = client.get("/api/v1/auth/user", headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["username"] == "testuser"
        assert "capabilities" in data

    def test_me_unauthorized(self, client, db):
        r = client.get("/api/v1/auth/user")
        assert r.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client, db):
        r = register_user_via_invite(client, db, "refreshtest", "refresh@example.com")
        refresh = r.get_json()["data"]["refresh_token"]
        r = client.post("/api/v1/auth/tokens", json={"refresh_token": refresh})
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client, db):
        r = client.post("/api/v1/auth/tokens", json={"refresh_token": "invalid"})
        assert r.status_code == 401

    def test_refresh_empty_body(self, client, db):
        r = client.post("/api/v1/auth/tokens", json={})
        assert r.status_code == 401


class TestLogout:
    def test_logout_success(self, client, db):
        r = register_user_via_invite(client, db, "logouttest", "logout@example.com")
        refresh = r.get_json()["data"]["refresh_token"]
        r = client.delete("/api/v1/auth/sessions", json={"refresh_token": refresh})
        assert r.status_code == 204

    def test_logout_no_refresh_token(self, client, db):
        r = client.delete("/api/v1/auth/sessions", json={})
        assert r.status_code == 400
