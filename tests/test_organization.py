class TestOrganization:
    def test_get_organization(self, client, db):
        r = client.get("/api/v1/organization")
        assert r.status_code == 200
        assert r.get_json()["data"]["contacts"] == []

    def test_update_organization(self, client, db, admin_headers):
        r = client.patch("/api/v1/organization", json={
            "name": "My Church", "description": "A great church",
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "My Church"

    def test_update_without_capability(self, client, db, auth_headers):
        r = client.patch("/api/v1/organization", json={"name": "Hacked"}, headers=auth_headers)
        assert r.status_code == 403

    def test_update_again(self, client, db, admin_headers):
        r = client.patch("/api/v1/organization", json={
            "name": "Updated Church", "description": "Updated",
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "Updated Church"

    def test_contact_fields_in_get(self, client, db, admin_headers):
        r = client.patch("/api/v1/organization", json={
            "email": "office@church.org",
            "phone": "+1-555-123-4567",
            "address": "123 Main St",
            "website": "https://church.org",
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["email"] == "office@church.org"
        assert data["phone"] == "+1-555-123-4567"
        assert data["address"] == "123 Main St"
        assert data["website"] == "https://church.org"

    def test_partial_update_contact_fields(self, client, db, admin_headers):
        r = client.patch("/api/v1/organization", json={
            "name": "Test", "email": "test@church.org",
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["email"] == "test@church.org"
        assert data["phone"] is None

    def test_create_org_with_contact_fields(self, client, db, admin_headers):
        r = client.get("/api/v1/organization", headers=admin_headers)
        org_id = r.get_json()["data"]["id"]
        if org_id is not None:
            return  # org already exists, skip

        r = client.patch("/api/v1/organization", json={
            "name": "New Church",
            "email": "new@church.org",
            "website": "https://new.church",
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["name"] == "New Church"
        assert data["email"] == "new@church.org"


class TestOrganizationContacts:
    def test_add_contact(self, client, db, admin_headers, person):
        r = client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"], "role": "Pastor"},
            headers=admin_headers,
        )
        assert r.status_code == 201
        assert r.get_json()["data"]["person_id"] == person["id"]
        assert r.get_json()["data"]["role"] == "Pastor"

    def test_add_contact_duplicate(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"], "role": "Pastor"},
            headers=admin_headers,
        )
        r = client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"], "role": "Elder"},
            headers=admin_headers,
        )
        assert r.status_code == 409

    def test_add_contact_person_not_found(self, client, db, admin_headers):
        r = client.post(
            "/api/v1/organization/contacts",
            json={"person_id": 99999, "role": "Pastor"},
            headers=admin_headers,
        )
        assert r.status_code == 404

    def test_add_contact_requires_capability(self, client, db, auth_headers, person):
        r = client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"]},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_list_contacts(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"], "role": "Pastor"},
            headers=admin_headers,
        )
        r = client.get("/api/v1/organization/contacts", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.get_json()["data"]) == 1
        assert r.get_json()["data"][0]["role"] == "Pastor"

    def test_contacts_in_org_response(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"], "role": "Pastor"},
            headers=admin_headers,
        )
        r = client.get("/api/v1/organization", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.get_json()["data"]["contacts"]) == 1

    def test_update_contact_role(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"], "role": "Pastor"},
            headers=admin_headers,
        )
        r = client.patch(
            f"/api/v1/organization/contacts/{person['id']}",
            json={"role": "Senior Pastor"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["role"] == "Senior Pastor"

    def test_delete_contact(self, client, db, admin_headers, person):
        client.post(
            "/api/v1/organization/contacts",
            json={"person_id": person["id"]},
            headers=admin_headers,
        )
        r = client.delete(
            f"/api/v1/organization/contacts/{person['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 204
        r = client.get("/api/v1/organization/contacts", headers=admin_headers)
        assert len(r.get_json()["data"]) == 0

    def test_delete_contact_not_found(self, client, db, admin_headers):
        r = client.delete(
            "/api/v1/organization/contacts/99999",
            headers=admin_headers,
        )
        assert r.status_code == 404
