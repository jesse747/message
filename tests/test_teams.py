class TestListTeams:
    def test_list_success(self, client, db, auth_headers):
        r = client.get("/api/v1/teams", headers=auth_headers)
        assert r.status_code == 200

    def test_list_search(self, client, db, auth_headers, team):
        r = client.get("/api/v1/teams?q=Test", headers=auth_headers)
        assert r.status_code == 200
        names = [t["name"] for t in r.get_json()["data"]]
        assert "Test Team" in names


class TestCreateTeam:
    def test_create_success(self, client, db, admin_headers):
        r = client.post("/api/v1/teams", json={"name": "New Team"}, headers=admin_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["name"] == "New Team"

    def test_create_without_capability(self, client, db, auth_headers):
        r = client.post("/api/v1/teams", json={"name": "No Perm Team"}, headers=auth_headers)
        assert r.status_code == 403

    def test_create_duplicate_name(self, client, db, admin_headers, team):
        r = client.post("/api/v1/teams", json={"name": "Test Team"}, headers=admin_headers)
        assert r.status_code == 409

    def test_create_validation_error(self, client, db, admin_headers):
        r = client.post("/api/v1/teams", json={}, headers=admin_headers)
        assert r.status_code == 422


class TestGetTeam:
    def test_get_success(self, client, db, auth_headers, team):
        r = client.get(f"/api/v1/teams/{team['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == team["id"]


class TestUpdateTeam:
    def test_update_success(self, client, db, admin_headers, team):
        r = client.patch(f"/api/v1/teams/{team['id']}", json={"description": "Updated desc"}, headers=admin_headers)
        assert r.status_code == 200


class TestDeleteTeam:
    def test_delete_success(self, client, db, admin_headers, team):
        r = client.delete(f"/api/v1/teams/{team['id']}", headers=admin_headers)
        assert r.status_code == 204


class TestTeamPersons:
    def test_add_person(self, client, db, admin_headers, team, person):
        r = client.post(f"/api/v1/teams/{team['id']}/persons", json={"person_id": person["id"]}, headers=admin_headers)
        assert r.status_code == 201

    def test_add_duplicate_person(self, client, db, admin_headers, team, person):
        client.post(f"/api/v1/teams/{team['id']}/persons", json={"person_id": person["id"]}, headers=admin_headers)
        r = client.post(f"/api/v1/teams/{team['id']}/persons", json={"person_id": person["id"]}, headers=admin_headers)
        assert r.status_code == 409

    def test_list_team_persons(self, client, db, auth_headers, team):
        r = client.get(f"/api/v1/teams/{team['id']}/persons", headers=auth_headers)
        assert r.status_code == 200

    def test_remove_person(self, client, db, admin_headers, team, person):
        client.post(f"/api/v1/teams/{team['id']}/persons", json={"person_id": person["id"]}, headers=admin_headers)
        r = client.delete(f"/api/v1/teams/{team['id']}/persons/{person['id']}", headers=admin_headers)
        assert r.status_code == 204

    def test_remove_no_capability(self, client, db, auth_headers, team, person):
        r = client.delete(f"/api/v1/teams/{team['id']}/persons/{person['id']}", headers=auth_headers)
        assert r.status_code == 403


class TestTeamMeetings:
    def test_list_meetings(self, client, db, auth_headers, team):
        r = client.get(f"/api/v1/teams/{team['id']}/meetings", headers=auth_headers)
        assert r.status_code == 200

    def test_create_meeting(self, client, db, admin_headers, team):
        r = client.post(f"/api/v1/teams/{team['id']}/meetings", json={
            "name": "Team Meeting", "day_of_week": 0, "frequency": "weekly",
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_create_meeting_ignores_body_fks(self, client, db, admin_headers, team):
        r = client.post(f"/api/v1/teams/{team['id']}/meetings", json={
            "name": "Team Meet", "day_of_week": 0, "team_id": 999, "group_id": 999,
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_create_meeting_no_capability(self, client, db, auth_headers, team):
        r = client.post(f"/api/v1/teams/{team['id']}/meetings", json={
            "name": "No Perm", "day_of_week": 0, "frequency": "weekly",
        }, headers=auth_headers)
        assert r.status_code == 403

    def test_create_meeting_auto_generates_instances(self, client, db, admin_headers, team):
        r = client.post(f"/api/v1/teams/{team['id']}/meetings", json={
            "name": "Team Meet", "day_of_week": 3, "frequency": "weekly",
        }, headers=admin_headers)
        assert r.status_code == 201
        instances = r.get_json()["data"]["instances"]
        assert len(instances) == 12


class TestTeamMeetingInstances:
    def test_list_instances(self, client, db, admin_headers, team):
        r = client.post(f"/api/v1/teams/{team['id']}/meetings", json={
            "name": "Team Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/teams/{team['id']}/meetings/{meeting_id}/instances", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.get_json()["data"]) == 12

    def test_create_manual_instance(self, client, db, admin_headers, team):
        r = client.post(f"/api/v1/teams/{team['id']}/meetings", json={
            "name": "Team Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/teams/{team['id']}/meetings/{meeting_id}/instances", json={
            "date": "2026-07-01",
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_cancel_team_instance_creates_post(self, client, db, admin_headers, team):
        r = client.post(f"/api/v1/teams/{team['id']}/meetings", json={
            "name": "Team Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        inst_id = r.get_json()["data"]["instances"][0]["id"]
        r = client.patch(f"/api/v1/teams/{team['id']}/meetings/{meeting_id}/instances/{inst_id}", json={
            "cancelled": True, "cancellation_message": "Team meeting cancelled",
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["cancelled"] is True
        r = client.get(f"/api/v1/teams/{team['id']}/posts", headers=admin_headers)
        posts = r.get_json()["data"]
        assert any("Team meeting cancelled" in p["content"] for p in posts)


class TestTeamAdmin:
    def test_team_admin_id_in_get(self, client, db, admin_headers, team):
        r = client.get(f"/api/v1/teams/{team['id']}", headers=admin_headers)
        assert r.status_code == 200
        assert "team_admin_id" in r.get_json()["data"]

    def test_team_admin_can_update(self, client, db, admin_headers, auth_headers, team):
        r = client.get("/api/v1/auth/user", headers=auth_headers)
        user_id = r.get_json()["data"]["id"]
        r = client.get("/api/v1/persons", headers=auth_headers)
        team_admin_person = next(p for p in r.get_json()["data"] if p["user_id"] == user_id)
        r = client.patch(
            f"/api/v1/teams/{team['id']}",
            json={"team_admin_id": team_admin_person["id"]},
            headers=admin_headers,
        )
        assert r.status_code == 200
        r = client.patch(
            f"/api/v1/teams/{team['id']}",
            json={"description": "Updated by team admin"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["description"] == "Updated by team admin"

    def test_team_admin_can_add_person(self, client, db, admin_headers, auth_headers, team, person):
        r = client.get("/api/v1/auth/user", headers=auth_headers)
        user_id = r.get_json()["data"]["id"]
        r = client.get("/api/v1/persons", headers=auth_headers)
        team_admin_person = next(p for p in r.get_json()["data"] if p["user_id"] == user_id)
        client.patch(
            f"/api/v1/teams/{team['id']}",
            json={"team_admin_id": team_admin_person["id"]},
            headers=admin_headers,
        )
        r = client.post(
            f"/api/v1/teams/{team['id']}/persons",
            json={"person_id": person["id"]},
            headers=auth_headers,
        )
        assert r.status_code == 201

    def test_non_admin_cannot_update(self, client, db, auth_headers, team):
        r = client.patch(
            f"/api/v1/teams/{team['id']}",
            json={"description": "Hacked"},
            headers=auth_headers,
        )
        assert r.status_code == 403


class TestTeamPosts:
    def test_list_posts(self, client, db, auth_headers, team):
        r = client.get(f"/api/v1/teams/{team['id']}/posts", headers=auth_headers)
        assert r.status_code == 200

    def test_create_post(self, client, db, admin_headers, team, person):
        # Admin adds the person to the team, then creates a post
        client.post(f"/api/v1/teams/{team['id']}/persons", json={"person_id": person["id"]}, headers=admin_headers)
        r = client.post(f"/api/v1/teams/{team['id']}/posts", json={"content": "Hello team!"}, headers=admin_headers)
        assert r.status_code == 201
