from tests.helpers import create_user


class TestListUsers:
    def test_list_success(self, client, db, auth_headers):
        r = client.get("/api/v1/users", headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert "data" in data
        assert "meta" in data

    def test_list_search(self, client, db, auth_headers):
        r = client.get("/api/v1/users?q=test", headers=auth_headers)
        assert r.status_code == 200
        usernames = [u["username"] for u in r.get_json()["data"]]
        assert "testuser" in usernames

    def test_list_unauthorized(self, client, db):
        r = client.get("/api/v1/users")
        assert r.status_code == 401


class TestGetUser:
    def test_get_success(self, client, db, auth_headers):
        r = client.get("/api/v1/users", headers=auth_headers)
        user_id = r.get_json()["data"][0]["id"]
        r = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == user_id

    def test_get_not_found(self, client, db, auth_headers):
        r = client.get("/api/v1/users/99999", headers=auth_headers)
        assert r.status_code == 404


class TestUpdateUser:
    def test_update_own_display_name(self, client, db, auth_headers):
        r = client.get("/api/v1/auth/user", headers=auth_headers)
        user_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/users/{user_id}", json={"display_name": "New Name"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["display_name"] == "New Name"

    def test_update_other_user_forbidden(self, client, db, auth_headers):
        create_user(db, "otheruser", "other@example.com")
        r = client.patch("/api/v1/users/2", json={"display_name": "Hacker"}, headers=auth_headers)
        assert r.status_code == 403
