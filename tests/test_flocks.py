class TestListFlocks:
    def test_list_success(self, client, db, auth_headers):
        r = client.get("/api/v1/flocks", headers=auth_headers)
        assert r.status_code == 200


class TestCreateFlock:
    def test_create_success(self, client, db, admin_headers):
        r = client.post("/api/v1/flocks", json={"name": "Young Adults"}, headers=admin_headers)
        assert r.status_code == 201

    def test_create_without_capability(self, client, db, auth_headers):
        r = client.post("/api/v1/flocks", json={"name": "No Perm"}, headers=auth_headers)
        assert r.status_code == 403


class TestGetFlock:
    def test_get_success(self, client, db, auth_headers, flock):
        r = client.get(f"/api/v1/flocks/{flock['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == flock["id"]


class TestUpdateFlock:
    def test_update_success(self, client, db, admin_headers, flock):
        r = client.patch(f"/api/v1/flocks/{flock['id']}", json={"description": "Updated flock"}, headers=admin_headers)
        assert r.status_code == 200


class TestDeleteFlock:
    def test_delete_success(self, client, db, admin_headers, flock):
        r = client.delete(f"/api/v1/flocks/{flock['id']}", headers=admin_headers)
        assert r.status_code == 204


class TestFlockMembers:
    def test_add_member(self, client, db, admin_headers, flock, person):
        r = client.post(f"/api/v1/flocks/{flock['id']}/members", json={"person_id": person["id"], "role": "member"}, headers=admin_headers)
        assert r.status_code == 201

    def test_add_duplicate_person(self, client, db, admin_headers, flock, person):
        client.post(f"/api/v1/flocks/{flock['id']}/members", json={"person_id": person["id"]}, headers=admin_headers)
        r = client.post(f"/api/v1/flocks/{flock['id']}/members", json={"person_id": person["id"]}, headers=admin_headers)
        assert r.status_code == 409

    def test_list_members(self, client, db, auth_headers, flock):
        r = client.get(f"/api/v1/flocks/{flock['id']}/members", headers=auth_headers)
        assert r.status_code == 200

    def test_update_member_role(self, client, db, admin_headers, flock, person):
        client.post(f"/api/v1/flocks/{flock['id']}/members", json={"person_id": person["id"], "role": "member"}, headers=admin_headers)
        r = client.patch(f"/api/v1/flocks/{flock['id']}/members/{person['id']}", json={"role": "shepherd"}, headers=admin_headers)
        assert r.status_code == 200

    def test_remove_member(self, client, db, admin_headers, flock, person):
        client.post(f"/api/v1/flocks/{flock['id']}/members", json={"person_id": person["id"]}, headers=admin_headers)
        r = client.delete(f"/api/v1/flocks/{flock['id']}/members/{person['id']}", headers=admin_headers)
        assert r.status_code == 204
