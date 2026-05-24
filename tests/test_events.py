class TestEvents:
    def test_list_events(self, client, db, auth_headers):
        r = client.get("/api/v1/events", headers=auth_headers)
        assert r.status_code == 200

    def test_create_event(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={
            "title": "Christmas Service",
            "frequency": "fixed",
            "fixed_month": 12,
            "fixed_day": 25,
        }, headers=admin_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["title"] == "Christmas Service"

    def test_create_without_capability(self, client, db, auth_headers):
        r = client.post("/api/v1/events", json={"title": "No Perm", "frequency": "none"}, headers=auth_headers)
        assert r.status_code == 403

    def test_get_event(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Easter", "frequency": "easter", "easter_offset": 0}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/events/{event_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["title"] == "Easter"

    def test_update_event(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Old Title", "frequency": "none"}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/events/{event_id}", json={"title": "New Title"}, headers=admin_headers)
        assert r.status_code == 200

    def test_delete_event(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Delete Me", "frequency": "none"}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/events/{event_id}", headers=admin_headers)
        assert r.status_code == 204


class TestOverrides:
    def test_create_override(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Event", "frequency": "none"}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/events/{event_id}/overrides", json={
            "date": "2026-06-15", "is_cancelled": True,
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_list_overrides(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Event2", "frequency": "none"}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/events/{event_id}/overrides", headers=admin_headers)
        assert r.status_code == 200

    def test_get_override(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Event3", "frequency": "none"}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/events/{event_id}/overrides", json={
            "date": "2026-07-01", "is_cancelled": False,
        }, headers=admin_headers)
        override_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/overrides/{override_id}", headers=admin_headers)
        assert r.status_code == 200

    def test_update_override(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Event4", "frequency": "none"}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/events/{event_id}/overrides", json={
            "date": "2026-08-01", "is_cancelled": False,
        }, headers=admin_headers)
        override_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/overrides/{override_id}", json={
            "is_cancelled": True, "override_title": "Cancelled",
        }, headers=admin_headers)
        assert r.status_code == 200

    def test_delete_override(self, client, db, admin_headers):
        r = client.post("/api/v1/events", json={"title": "Event5", "frequency": "none"}, headers=admin_headers)
        event_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/events/{event_id}/overrides", json={
            "date": "2026-09-01", "is_cancelled": False,
        }, headers=admin_headers)
        override_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/overrides/{override_id}", headers=admin_headers)
        assert r.status_code == 204
