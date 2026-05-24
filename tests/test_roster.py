class TestDutyGroups:
    def test_list_duty_groups(self, client, db, auth_headers):
        r = client.get("/api/v1/duty-groups", headers=auth_headers)
        assert r.status_code == 200

    def test_create_duty_group(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={
            "name": "Sunday AM", "day_of_week": 6, "time": "09:00",
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_create_without_capability(self, client, db, auth_headers):
        r = client.post("/api/v1/duty-groups", json={
            "name": "No Perm", "day_of_week": 0,
        }, headers=auth_headers)
        assert r.status_code == 403

    def test_get_duty_group(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={
            "name": "Evening", "day_of_week": 6, "time": "18:00",
        }, headers=admin_headers)
        dg_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/duty-groups/{dg_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["name"] == "Evening"

    def test_update_duty_group(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={
            "name": "Old Group", "day_of_week": 0,
        }, headers=admin_headers)
        dg_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/duty-groups/{dg_id}", json={"name": "New Group"}, headers=admin_headers)
        assert r.status_code == 200

    def test_delete_duty_group(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={
            "name": "Delete Group", "day_of_week": 0,
        }, headers=admin_headers)
        dg_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/duty-groups/{dg_id}", headers=admin_headers)
        assert r.status_code == 204


class TestDuties:
    def test_create_duty(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={"name": "Service", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={
            "name": "Worship Leader", "sort_order": 1,
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_list_duties(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={"name": "Service2", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/duty-groups/{group_id}/duties", headers=admin_headers)
        assert r.status_code == 200

    def test_get_duty(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={"name": "Service3", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={"name": "Drums", "sort_order": 1}, headers=admin_headers)
        duty_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/duties/{duty_id}", headers=admin_headers)
        assert r.status_code == 200

    def test_update_duty(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={"name": "Service4", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={"name": "Old", "sort_order": 1}, headers=admin_headers)
        duty_id = r.get_json()["data"]["id"]
        r = client.patch(f"/api/v1/duties/{duty_id}", json={"name": "New Name"}, headers=admin_headers)
        assert r.status_code == 200

    def test_delete_duty(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={"name": "Service5", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={"name": "Delete", "sort_order": 1}, headers=admin_headers)
        duty_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/duties/{duty_id}", headers=admin_headers)
        assert r.status_code == 204


class TestMemberships:
    def test_create_membership(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "RosterGroup", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/memberships", json={
            "person_id": person["id"], "date_from": "2026-06-01",
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_list_memberships(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "RG2", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/duty-groups/{group_id}/memberships", headers=admin_headers)
        assert r.status_code == 200

    def test_get_membership(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "RG3", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/memberships", json={
            "person_id": person["id"], "date_from": "2026-06-01",
        }, headers=admin_headers)
        m_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/memberships/{m_id}", headers=admin_headers)
        assert r.status_code == 200

    def test_delete_membership(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "RG4", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/memberships", json={
            "person_id": person["id"], "date_from": "2026-06-01",
        }, headers=admin_headers)
        m_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/memberships/{m_id}", headers=admin_headers)
        assert r.status_code == 204


class TestAssignments:
    def test_create_assignment(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "AssignGroup", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={"name": "Singer", "sort_order": 1}, headers=admin_headers)
        duty_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duties/{duty_id}/assignments", json={
            "person_id": person["id"], "date": "2026-06-07",
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_list_assignments(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "AG2", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={"name": "Guitar", "sort_order": 1}, headers=admin_headers)
        duty_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/duties/{duty_id}/assignments", headers=admin_headers)
        assert r.status_code == 200

    def test_get_assignment(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "AG3", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={"name": "Keys", "sort_order": 1}, headers=admin_headers)
        duty_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duties/{duty_id}/assignments", json={
            "person_id": person["id"], "date": "2026-06-14",
        }, headers=admin_headers)
        a_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/assignments/{a_id}", headers=admin_headers)
        assert r.status_code == 200

    def test_delete_assignment(self, client, db, admin_headers, person):
        r = client.post("/api/v1/duty-groups", json={"name": "AG4", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={"name": "Bass", "sort_order": 1}, headers=admin_headers)
        duty_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duties/{duty_id}/assignments", json={
            "person_id": person["id"], "date": "2026-06-21",
        }, headers=admin_headers)
        a_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/assignments/{a_id}", headers=admin_headers)
        assert r.status_code == 204


class TestRoster:
    def test_get_roster_success(self, client, db, admin_headers):
        r = client.post("/api/v1/duty-groups", json={"name": "RosterView", "day_of_week": 6}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.get(
            f"/api/v1/roster?group_id={group_id}&date_from=2026-06-01&date_to=2026-06-28",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["group"]["name"] == "RosterView"

    def test_get_roster_missing_params(self, client, db, auth_headers):
        r = client.get("/api/v1/roster", headers=auth_headers)
        assert r.status_code == 400
