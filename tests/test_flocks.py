class TestListFlocks:
    def test_list_success(self, client, db, auth_headers):
        r = client.get("/api/v1/flocks", headers=auth_headers)
        assert r.status_code == 200
        assert "data" in r.get_json()
        assert "meta" in r.get_json()
        assert "page" in r.get_json()["meta"]
        assert "total" in r.get_json()["meta"]


class TestCreateFlock:
    def test_create_success(self, client, db, admin_headers):
        r = client.post(
            "/api/v1/flocks",
            json={"name": "Young Adults"},
            headers=admin_headers,
        )
        assert r.status_code == 201
        assert r.get_json()["data"]["name"] == "Young Adults"

    def test_create_with_shepherd(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/flocks",
            json={"name": "Shepherd Flock", "shepherd_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["shepherd_id"] == person["id"]
        assert data["shepherd_name"] == "John Doe"

    def test_create_shepherd_uniqueness(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/flocks",
            json={"name": "Flock A", "shepherd_id": person["id"]},
            headers=admin_headers,
        )
        r = client.post(
            "/api/v1/flocks",
            json={"name": "Flock B", "shepherd_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 409

    def test_create_without_capability(self, client, db, auth_headers):
        r = client.post(
            "/api/v1/flocks",
            json={"name": "No Perm"},
            headers=auth_headers,
        )
        assert r.status_code == 403


class TestGetFlock:
    def test_get_success(self, client, db, auth_headers, flock):
        r = client.get(f"/api/v1/flocks/{flock['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == flock["id"]

    def test_get_with_shepherd(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/flocks",
            json={"name": "Shepherd Flock Get", "shepherd_id": person["id"]},
            headers=admin_headers,
        )
        fid = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/flocks/{fid}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["shepherd_name"] == "John Doe"


class TestUpdateFlock:
    def test_update_success(self, client, db, admin_headers, flock):
        r = client.patch(
            f"/api/v1/flocks/{flock['id']}",
            json={"description": "Updated flock"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["description"] == "Updated flock"

    def test_update_set_shepherd(self, client, db, admin_headers, flock, person):
        r = client.patch(
            f"/api/v1/flocks/{flock['id']}",
            json={"shepherd_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["shepherd_id"] == person["id"]
        assert r.get_json()["data"]["shepherd_name"] == "John Doe"

    def test_update_clear_shepherd(self, client, db, admin_headers, flock, person):
        client.patch(
            f"/api/v1/flocks/{flock['id']}",
            json={"shepherd_id": person["id"]},
            headers=admin_headers,
        )
        r = client.patch(
            f"/api/v1/flocks/{flock['id']}",
            json={"shepherd_id": None},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["shepherd_id"] is None
        assert r.get_json()["data"]["shepherd_name"] is None

    def test_update_shepherd_uniqueness(self, client, db, admin_headers, person):
        r1 = client.post(
            "/api/v1/flocks",
            json={"name": "Flock One"},
            headers=admin_headers,
        )
        fid1 = r1.get_json()["data"]["id"]
        r2 = client.post(
            "/api/v1/flocks",
            json={"name": "Flock Two"},
            headers=admin_headers,
        )
        fid2 = r2.get_json()["data"]["id"]
        client.patch(
            f"/api/v1/flocks/{fid1}",
            json={"shepherd_id": person["id"]},
            headers=admin_headers,
        )
        r = client.patch(
            f"/api/v1/flocks/{fid2}",
            json={"shepherd_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 409


class TestDeleteFlock:
    def test_delete_success(self, client, db, admin_headers, flock):
        r = client.delete(f"/api/v1/flocks/{flock['id']}", headers=admin_headers)
        assert r.status_code == 204


class TestFlockMembers:
    def test_add_member(self, client, db, admin_headers, flock, person):
        r = client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 201

    def test_add_duplicate_person(self, client, db, admin_headers, flock, person):
        client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        r = client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 409

    def test_list_members(self, client, db, auth_headers, flock):
        r = client.get(
            f"/api/v1/flocks/{flock['id']}/members", headers=auth_headers
        )
        assert r.status_code == 200

    def test_update_member_notes(self, client, db, admin_headers, flock, person):
        client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        r = client.patch(
            f"/api/v1/flocks/{flock['id']}/members/{person['id']}",
            json={"notes": "Active member"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["notes"] == "Active member"

    def test_remove_member(self, client, db, admin_headers, flock, person):
        client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        r = client.delete(
            f"/api/v1/flocks/{flock['id']}/members/{person['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 204


class TestFlockBatchMembers:
    def test_batch_add_success(self, client, db, admin_headers, flock, person):
        r2 = client.post(
            "/api/v1/persons",
            json={"first_name": "Jane", "last_name": "Smith"},
            headers=admin_headers,
        )
        person2 = r2.get_json()["data"]
        r = client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_ids": [person["id"], person2["id"]]},
            headers=admin_headers,
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["added"] == 2
        assert len(data["members"]) == 2

    def test_batch_add_empty(self, client, db, admin_headers, flock):
        r = client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_ids": []},
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_batch_add_non_existent(self, client, db, admin_headers, flock, person):
        r = client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_ids": [person["id"], 99999]},
            headers=admin_headers,
        )
        assert r.status_code == 404

    def test_batch_add_already_in_flock(
        self, client, db, admin_headers, flock, person
    ):
        client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        r2 = client.post(
            "/api/v1/persons",
            json={"first_name": "Jane", "last_name": "Smith"},
            headers=admin_headers,
        )
        person2 = r2.get_json()["data"]
        r = client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_ids": [person["id"], person2["id"]]},
            headers=admin_headers,
        )
        assert r.status_code == 409

    def test_batch_deduplicates(
        self, client, db, admin_headers, flock, person
    ):
        r = client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_ids": [person["id"], person["id"]]},
            headers=admin_headers,
        )
        assert r.status_code == 201
        assert r.get_json()["data"]["added"] == 1


class TestAvailableMembers:
    def test_list_unassigned(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/flocks",
            json={"name": "Test Flock"},
            headers=admin_headers,
        )
        fid = r.get_json()["data"]["id"]
        r = client.get(
            f"/api/v1/flocks/{fid}/available-members", headers=admin_headers
        )
        assert r.status_code == 200
        assert len(r.get_json()["data"]) >= 1
        ids = [p["id"] for p in r.get_json()["data"]]
        assert person["id"] in ids

    def test_available_excludes_assigned(
        self, client, db, admin_headers, flock, person
    ):
        client.post(
            f"/api/v1/flocks/{flock['id']}/members",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        r = client.get(
            f"/api/v1/flocks/{flock['id']}/available-members",
            headers=admin_headers,
        )
        ids = [p["id"] for p in r.get_json()["data"]]
        assert person["id"] not in ids

    def test_available_flock_not_found(self, client, db, admin_headers):
        r = client.get(
            "/api/v1/flocks/99999/available-members", headers=admin_headers
        )
        assert r.status_code == 404
