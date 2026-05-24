class TestListEventTypes:
    def test_list_active(self, client, db, auth_headers, event_type):
        r = client.get("/api/v1/event-types", headers=auth_headers)
        assert r.status_code == 200
        body = r.get_json()
        assert "meta" in body
        event_types = body["data"]
        assert any(et["name"] == "Baptism" for et in event_types)
        assert all(et["is_active"] for et in event_types)

    def test_list_all(self, client, db, admin_headers, event_type):
        r = client.get("/api/v1/event-types", headers=admin_headers)
        ets = r.get_json()["data"]
        client.patch(
            f"/api/v1/event-types/{ets[0]['id']}",
            json={"is_active": False},
            headers=admin_headers,
        )
        r = client.get("/api/v1/event-types?all=true", headers=admin_headers)
        assert r.status_code == 200
        active = [et for et in r.get_json()["data"] if et["is_active"]]
        inactive = [et for et in r.get_json()["data"] if not et["is_active"]]
        assert len(active) >= 1
        assert len(inactive) >= 1


class TestGetEventType:
    def test_get_success(self, client, db, auth_headers, event_type):
        r = client.get(
            f"/api/v1/event-types/{event_type['id']}", headers=auth_headers
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["id"] == event_type["id"]
        assert data["name"] == event_type["name"]

    def test_get_not_found(self, client, db, auth_headers):
        r = client.get("/api/v1/event-types/99999", headers=auth_headers)
        assert r.status_code == 404


class TestCreateEventType:
    def test_create_success(self, client, db, admin_headers):
        r = client.post(
            "/api/v1/event-types",
            json={"name": "Test Event", "description": "A test event", "sort_order": 5},
            headers=admin_headers,
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["name"] == "Test Event"
        assert data["description"] == "A test event"
        assert data["sort_order"] == 5
        assert data["is_active"] is True

    def test_create_without_capability(self, client, db, auth_headers):
        r = client.post(
            "/api/v1/event-types",
            json={"name": "Test Event"},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_create_duplicate_name(self, client, db, admin_headers):
        client.post(
            "/api/v1/event-types",
            json={"name": "Unique Event"},
            headers=admin_headers,
        )
        r = client.post(
            "/api/v1/event-types",
            json={"name": "Unique Event"},
            headers=admin_headers,
        )
        assert r.status_code == 409

    def test_create_validation_error(self, client, db, admin_headers):
        r = client.post("/api/v1/event-types", json={}, headers=admin_headers)
        assert r.status_code == 422


class TestUpdateEventType:
    def test_update_success(self, client, db, admin_headers, event_type):
        r = client.patch(
            f"/api/v1/event-types/{event_type['id']}",
            json={"name": "Updated Name", "description": "Updated desc"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated desc"

    def test_update_duplicate_name(self, client, db, admin_headers, event_type):
        r = client.get("/api/v1/event-types", headers=admin_headers)
        event_types = r.get_json()["data"]
        et1 = event_types[0]
        et2 = event_types[1]
        r = client.patch(
            f"/api/v1/event-types/{et1['id']}",
            json={"name": et2["name"]},
            headers=admin_headers,
        )
        assert r.status_code == 409

    def test_update_not_found(self, client, db, admin_headers):
        r = client.patch(
            "/api/v1/event-types/99999",
            json={"name": "X"},
            headers=admin_headers,
        )
        assert r.status_code == 404


class TestDeleteEventType:
    def test_delete_soft(self, client, db, admin_headers, event_type):
        r = client.post(
            "/api/v1/event-types",
            json={"name": "To Delete"},
            headers=admin_headers,
        )
        et_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/event-types/{et_id}", headers=admin_headers)
        assert r.status_code == 204
        r = client.get("/api/v1/event-types", headers=admin_headers)
        names = [et["name"] for et in r.get_json()["data"]]
        assert "To Delete" not in names

    def test_delete_not_found(self, client, db, admin_headers):
        r = client.delete("/api/v1/event-types/99999", headers=admin_headers)
        assert r.status_code == 404
