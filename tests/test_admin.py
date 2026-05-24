import secrets
from datetime import UTC, datetime, timedelta

from src.message.models import InviteToken, Person
from tests.helpers import create_user, register_user_via_invite


class TestAuthAttempts:
    def test_list_auth_attempts_as_admin(self, client, db, admin_headers):
        r = client.get("/api/v1/admin/auth-attempts", headers=admin_headers)
        assert r.status_code == 200
        assert "data" in r.get_json()

    def test_list_auth_attempts_without_capability(self, client, db, auth_headers):
        r = client.get("/api/v1/admin/auth-attempts", headers=auth_headers)
        assert r.status_code == 403


class TestCreateInvite:
    def test_create_invite_success(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=admin_headers,
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["person_id"] == person["id"]
        assert data["email"] == person["email_personal"]
        assert data["is_active"] is True
        assert data["is_used"] is False
        assert data["is_expired"] is False
        assert "code" in data
        assert "expires_at" in data
        assert "created_at" in data

    def test_create_invite_custom_expiry(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={
                "person_id": person["id"],
                "email": person["email_personal"],
                "expires_in_days": 30,
            },
            headers=admin_headers,
        )
        assert r.status_code == 201

    def test_create_invite_without_capability(self, client, db, auth_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_create_invite_person_not_found(self, client, db, admin_headers):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": 99999, "email": "x@example.com"},
            headers=admin_headers,
        )
        assert r.status_code == 404

    def test_create_invite_person_already_has_user(self, client, db, admin_headers):
        user = create_user(db, "alreadyuser", "already@example.com")
        person = Person.query.filter_by(user_id=user.id).first()
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person.id, "email": "already@example.com"},
            headers=admin_headers,
        )
        assert r.status_code == 409
        assert r.get_json()["error"]["code"] == "CONFLICT"

    def test_create_invite_missing_fields(self, client, db, admin_headers):
        r = client.post(
            "/api/v1/admin/invites",
            json={},
            headers=admin_headers,
        )
        assert r.status_code == 422

        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": 1},
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_create_invite_sends_email(self, app, client, db, admin_headers, person):
        from src.message.extensions import mail

        with mail.record_messages() as outbox:
            r = client.post(
                "/api/v1/admin/invites",
                json={"person_id": person["id"], "email": person["email_personal"]},
                headers=admin_headers,
            )
            assert r.status_code == 201

        assert len(outbox) == 1
        msg = outbox[0]
        assert msg.recipients == [person["email_personal"]]
        assert r.get_json()["data"]["code"] in msg.body
        assert person["first_name"] in msg.body


class TestListInvites:
    def test_list_all_invites(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=admin_headers,
        )
        r = client.get("/api/v1/admin/invites", headers=admin_headers)
        assert r.status_code == 200
        body = r.get_json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["total"] >= 1

    def test_list_invites_filter_active(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=admin_headers,
        )
        r = client.get("/api/v1/admin/invites?status=active", headers=admin_headers)
        assert r.status_code == 200
        for invite in r.get_json()["data"]:
            assert invite["is_active"] is True
            assert invite["is_used"] is False

    def test_list_invites_filter_used(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=admin_headers,
        )
        code = r.get_json()["data"]["code"]
        client.post(
            "/api/v1/auth/users",
            json={
                "invite_code": code,
                "email": person["email_personal"],
                "username": "inviteduser",
                "password": "password123",
            },
        )
        r = client.get("/api/v1/admin/invites?status=used", headers=admin_headers)
        assert r.status_code == 200
        used = r.get_json()["data"]
        assert len(used) >= 1
        assert all(i["is_used"] for i in used)

    def test_list_invites_filter_expired(self, client, db, admin_headers, person):
        from src.message.extensions import db as ext_db

        invite = InviteToken(
            code=secrets.token_urlsafe(32),
            person_id=person["id"],
            email=person["email_personal"],
            created_by=1,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        ext_db.session.add(invite)
        ext_db.session.commit()

        r = client.get("/api/v1/admin/invites?status=expired", headers=admin_headers)
        assert r.status_code == 200
        for i in r.get_json()["data"]:
            assert i["is_expired"] is True
            assert i["is_used"] is False

    def test_list_invites_pagination(self, client, db, admin_headers, person):
        for _ in range(3):
            client.post(
                "/api/v1/admin/invites",
                json={"person_id": person["id"], "email": person["email_personal"]},
                headers=admin_headers,
            )
        r = client.get(
            "/api/v1/admin/invites?page=1&limit=2", headers=admin_headers
        )
        assert r.status_code == 200
        meta = r.get_json()["meta"]
        assert meta["page"] == 1
        assert meta["limit"] == 2
        assert len(r.get_json()["data"]) <= 2

    def test_list_invites_without_capability(self, client, db, auth_headers):
        r = client.get("/api/v1/admin/invites", headers=auth_headers)
        assert r.status_code == 403


class TestGetInvite:
    def test_get_invite_success(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=admin_headers,
        )
        invite_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/admin/invites/{invite_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == invite_id

    def test_get_invite_not_found(self, client, db, admin_headers):
        r = client.get("/api/v1/admin/invites/99999", headers=admin_headers)
        assert r.status_code == 404

    def test_get_invite_without_capability(self, client, db, auth_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=auth_headers,  # this will fail, but we need an existing id
        )
        r = client.get("/api/v1/admin/invites/1", headers=auth_headers)
        assert r.status_code == 403


class TestRevokeInvite:
    def test_revoke_invite_success(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=admin_headers,
        )
        invite_id = r.get_json()["data"]["id"]
        r = client.delete(
            f"/api/v1/admin/invites/{invite_id}", headers=admin_headers
        )
        assert r.status_code == 204

        r = client.get(f"/api/v1/admin/invites/{invite_id}", headers=admin_headers)
        assert r.get_json()["data"]["is_active"] is False

    def test_revoke_invite_not_found(self, client, db, admin_headers):
        r = client.delete("/api/v1/admin/invites/99999", headers=admin_headers)
        assert r.status_code == 404

    def test_revoke_invite_already_used(self, client, db, admin_headers):
        register_user_via_invite(client, db, "revokeduser", "revoked@example.com")

        r = client.get("/api/v1/admin/invites?status=used", headers=admin_headers)
        used = r.get_json()["data"]
        if not used:
            return
        r = client.delete(
            f"/api/v1/admin/invites/{used[0]['id']}", headers=admin_headers
        )
        assert r.status_code == 409
        assert r.get_json()["error"]["code"] == "CONFLICT"

    def test_revoke_invite_without_capability(self, client, db, auth_headers, person):
        r = client.post(
            "/api/v1/admin/invites",
            json={"person_id": person["id"], "email": person["email_personal"]},
            headers=auth_headers,  # fails, but we need the concept
        )
        r = client.delete("/api/v1/admin/invites/1", headers=auth_headers)
        assert r.status_code == 403
