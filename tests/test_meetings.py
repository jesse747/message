class TestMeetings:
    def test_get_meeting(self, client, db, admin_headers, team):
        r = client.post(
            f"/api/v1/teams/{team['id']}/meetings",
            json={"name": "Sunday Service", "day_of_week": 6, "frequency": "weekly"},
            headers=admin_headers,
        )
        meeting_id = r.get_json()["data"]["id"]

        r = client.get(f"/api/v1/meetings/{meeting_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "Sunday Service"

    def test_update_meeting(self, client, db, admin_headers, team):
        r = client.post(
            f"/api/v1/teams/{team['id']}/meetings",
            json={"name": "Old Name", "day_of_week": 0, "frequency": "weekly"},
            headers=admin_headers,
        )
        meeting_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/meetings/{meeting_id}", json={"name": "New Name"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "New Name"

    def test_delete_meeting(self, client, db, admin_headers, team):
        r = client.post(
            f"/api/v1/teams/{team['id']}/meetings",
            json={"name": "Delete Me", "day_of_week": 3, "frequency": "weekly"},
            headers=admin_headers,
        )
        meeting_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/meetings/{meeting_id}", headers=admin_headers)
        assert r.status_code == 204

    def test_get_not_found(self, client, db, auth_headers):
        r = client.get("/api/v1/meetings/99999", headers=auth_headers)
        assert r.status_code == 404
