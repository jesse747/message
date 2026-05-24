import io


class TestFileOperations:
    def test_upload_to_team(self, client, db, admin_headers, team):
        data = {"file": (io.BytesIO(b"test content"), "test.txt")}
        r = client.post(
            f"/api/v1/teams/{team['id']}/files",
            data=data,
            content_type="multipart/form-data",
            headers=admin_headers,
        )
        assert r.status_code == 201
        result = r.get_json()["data"]
        assert len(result) == 1
        assert result[0]["name"] == "test.txt"
        file_id = result[0]["id"]

        r = client.get(f"/api/v1/files/{file_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "test.txt"

    def test_upload_no_file(self, client, db, team, auth_headers):
        r = client.post(
            f"/api/v1/teams/{team['id']}/files",
            data={},
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_upload_wrong_content_type(self, client, db, team, auth_headers):
        r = client.post(
            f"/api/v1/teams/{team['id']}/files",
            json={"file": "not a file"},
            headers=auth_headers,
        )
        assert r.status_code == 415

    def test_download_file(self, client, db, admin_headers, team):
        data = {"file": (io.BytesIO(b"download content"), "down.txt")}
        r = client.post(
            f"/api/v1/teams/{team['id']}/files",
            data=data,
            content_type="multipart/form-data",
            headers=admin_headers,
        )
        file_id = r.get_json()["data"][0]["id"]
        r = client.get(f"/api/v1/files/{file_id}/download", headers=admin_headers)
        assert r.status_code == 200

    def test_get_file_info(self, client, db, admin_headers, team):
        data = {"file": (io.BytesIO(b"info content"), "info.txt")}
        r = client.post(
            f"/api/v1/teams/{team['id']}/files",
            data=data,
            content_type="multipart/form-data",
            headers=admin_headers,
        )
        file_id = r.get_json()["data"][0]["id"]
        r = client.get(f"/api/v1/files/{file_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "info.txt"

    def test_delete_file(self, client, db, admin_headers, team):
        data = {"file": (io.BytesIO(b"delete content"), "del.txt")}
        r = client.post(
            f"/api/v1/teams/{team['id']}/files",
            data=data,
            content_type="multipart/form-data",
            headers=admin_headers,
        )
        file_id = r.get_json()["data"][0]["id"]
        r = client.delete(f"/api/v1/files/{file_id}", headers=admin_headers)
        assert r.status_code == 204

    def test_upload_to_post(self, client, db, auth_headers):
        r = client.post("/api/v1/posts", json={"content": "Post with file"}, headers=auth_headers)
        post_id = r.get_json()["data"]["id"]
        data = {"file": (io.BytesIO(b"post file"), "postfile.txt")}
        r = client.post(
            f"/api/v1/posts/{post_id}/files",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert r.status_code == 201
