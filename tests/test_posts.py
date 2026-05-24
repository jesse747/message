from flask_jwt_extended import create_access_token
from tests.helpers import create_user


class TestListPosts:
    def test_list_success(self, client, db, auth_headers):
        r = client.get("/api/v1/posts", headers=auth_headers)
        assert r.status_code == 200

    def test_list_pagination(self, client, db, auth_headers):
        r = client.get("/api/v1/posts?page=1&limit=5", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["meta"]["page"] == 1


class TestCreatePost:
    def test_create_success(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": "Test announcement"}, headers=auth_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["content"] == "Test announcement"

    def test_create_empty_content(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": ""}, headers=auth_headers)
        assert r.status_code == 422

    def test_create_missing_content(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={}, headers=auth_headers)
        assert r.status_code == 422


class TestGetPost:
    def test_get_success(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": "Get test"}, headers=auth_headers)
        post_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/posts/{post_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == post_id


class TestUpdatePost:
    def test_update_own_post(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": "Original"}, headers=auth_headers)
        post_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/posts/{post_id}", json={"content": "Updated"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["content"] == "Updated"

    def test_update_other_post_forbidden(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": "Mine"}, headers=auth_headers)
        post_id = r.get_json()["data"]["id"]
        other_user = create_user(db, "otherposter", "op@example.com")
        other_token = create_access_token(identity=str(other_user.id))
        other_headers = {"Authorization": f"Bearer {other_token}"}
        r = client.patch(f"/api/v1/posts/{post_id}", json={"content": "Hacked"}, headers=other_headers)
        assert r.status_code == 403


class TestDeletePost:
    def test_delete_own_post(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": "To delete"}, headers=auth_headers)
        post_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/posts/{post_id}", headers=auth_headers)
        assert r.status_code == 204

    def test_delete_other_post_forbidden(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": "Mine"}, headers=auth_headers)
        post_id = r.get_json()["data"]["id"]
        other_user = create_user(db, "otherdel", "od@example.com")
        other_token = create_access_token(identity=str(other_user.id))
        other_headers = {"Authorization": f"Bearer {other_token}"}
        r = client.delete(f"/api/v1/posts/{post_id}", headers=other_headers)
        assert r.status_code == 403
