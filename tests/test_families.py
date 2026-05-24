class TestListFamilies:
    def test_list_empty(self, client, db, auth_headers):
        r = client.get("/api/v1/families", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["meta"]["total"] == 0

    def test_list_with_data(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        assert r.status_code == 201
        r = client.get("/api/v1/families", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["meta"]["total"] == 1

    def test_list_search(self, client, db, admin_headers):
        client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        client.post("/api/v1/families", json={"name": "Jones Family"}, headers=admin_headers)
        r = client.get("/api/v1/families?q=Jones", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["meta"]["total"] == 1

    def test_list_pagination(self, client, db, admin_headers):
        for name in ["A", "B", "C"]:
            client.post("/api/v1/families", json={"name": f"{name} Family"}, headers=admin_headers)
        r = client.get("/api/v1/families?page=1&limit=2", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.get_json()["data"]) == 2
        assert r.get_json()["meta"]["pages"] == 2


class TestCreateFamily:
    def test_create_success(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["name"] == "Smith Family"

    def test_create_with_head(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/families",
            json={"name": "Smith Family", "head_person_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 201
        assert r.get_json()["data"]["head_person_id"] == person["id"]

    def test_create_requires_name(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={}, headers=admin_headers)
        assert r.status_code == 422

    def test_create_requires_capability(self, client, db, auth_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=auth_headers)
        assert r.status_code == 403

    def test_create_head_not_found(self, client, db, admin_headers):
        r = client.post(
            "/api/v1/families",
            json={"name": "Ghost Family", "head_person_id": 99999},
            headers=admin_headers,
        )
        assert r.status_code == 404

    def test_create_duplicate_head(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/families",
            json={"name": "First Family", "head_person_id": person["id"]},
            headers=admin_headers,
        )
        r = client.post(
            "/api/v1/families",
            json={"name": "Second Family", "head_person_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 409


class TestGetFamily:
    def test_get_success(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/families/{fam_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "Smith Family"

    def test_get_with_members(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r1 = client.post("/api/v1/persons", json={"first_name": "John", "last_name": "Smith"}, headers=admin_headers)
        r2 = client.post("/api/v1/persons", json={"first_name": "Jane", "last_name": "Smith"}, headers=admin_headers)
        p1 = r1.get_json()["data"]["id"]
        p2 = r2.get_json()["data"]["id"]
        client.patch(f"/api/v1/persons/{p1}", json={"family_id": fam_id}, headers=admin_headers)
        client.patch(f"/api/v1/persons/{p2}", json={"family_id": fam_id}, headers=admin_headers)
        r = client.get(f"/api/v1/families/{fam_id}", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.get_json()["data"]["members"]) == 2

    def test_get_not_found(self, client, db, auth_headers):
        r = client.get("/api/v1/families/99999", headers=auth_headers)
        assert r.status_code == 404


class TestUpdateFamily:
    def test_update_name(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/families/{fam_id}", json={"name": "Jones Family"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "Jones Family"

    def test_update_head(self, client, db, admin_headers, person):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r = client.patch(
            f"/api/v1/families/{fam_id}",
            json={"head_person_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["head_person_id"] == person["id"]

    def test_update_requires_capability(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/families/{fam_id}", json={"name": "X"}, headers=auth_headers)
        assert r.status_code == 403


class TestDeleteFamily:
    def test_delete_success(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/families/{fam_id}", headers=admin_headers)
        assert r.status_code == 204

    def test_delete_requires_capability(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/families/{fam_id}", headers=auth_headers)
        assert r.status_code == 403


class TestFamilyPhoto:
    def test_upload_photo(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        import io
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        r = client.post(
            f"/api/v1/families/{fam_id}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        assert r.status_code == 201
        assert r.get_json()["data"]["photo_url"] is not None

    def test_upload_requires_capability(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        import io
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        r = client.post(
            f"/api/v1/families/{fam_id}/photo",
            headers={**auth_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        assert r.status_code == 403

    def test_get_photo(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        import io
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        client.post(
            f"/api/v1/families/{fam_id}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        r = client.get(f"/api/v1/families/{fam_id}/photo", headers=admin_headers)
        assert r.status_code == 200
        assert r.data == b"fake-image-data"

    def test_get_photo_no_photo(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/families/{fam_id}/photo", headers=admin_headers)
        assert r.status_code == 404

    def test_delete_photo(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        import io
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        client.post(
            f"/api/v1/families/{fam_id}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        r = client.delete(f"/api/v1/families/{fam_id}/photo", headers=admin_headers)
        assert r.status_code == 204
        r = client.get(f"/api/v1/families/{fam_id}/photo", headers=admin_headers)
        assert r.status_code == 404

    def test_photo_url_in_detail(self, client, db, admin_headers):
        r = client.post("/api/v1/families", json={"name": "Smith Family"}, headers=admin_headers)
        fam_id = r.get_json()["data"]["id"]
        import io
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        client.post(
            f"/api/v1/families/{fam_id}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        r = client.get(f"/api/v1/families/{fam_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["photo_url"] is not None
