

class TestSwapAssignments:
    def create_fixtures(self, client, admin_headers):
        r = client.post("/api/v1/duty-groups", json={
            "name": "Ushers", "day_of_week": 0,
        }, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={
            "name": "Welcome Lead",
        }, headers=admin_headers)
        duty1_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={
            "name": "Sound Operator",
        }, headers=admin_headers)
        duty2_id = r.get_json()["data"]["id"]
        r = client.post("/api/v1/persons", json={
            "first_name": "Alice", "last_name": "A",
        }, headers=admin_headers)
        person_a = r.get_json()["data"]["id"]
        r = client.post("/api/v1/persons", json={
            "first_name": "Bob", "last_name": "B",
        }, headers=admin_headers)
        person_b = r.get_json()["data"]["id"]
        return duty1_id, duty2_id, person_a, person_b

    def assign(self, client, admin_headers, duty_id, person_id, date):
        r = client.post(f"/api/v1/duties/{duty_id}/assignments", json={
            "person_id": person_id, "date": date,
        }, headers=admin_headers)
        return r

    def swap(self, client, headers, date, changes):
        return client.post("/api/v1/assignments/swap", json={
            "date": date, "changes": changes,
        }, headers=headers)

    def test_simple_substitution(self, client, db, admin_headers):
        duty1, _, alice, bob = self.create_fixtures(client, admin_headers)
        self.assign(client, admin_headers, duty1, alice, "2026-06-07")
        r = self.swap(client, admin_headers, "2026-06-07", [
            {"duty_id": duty1, "from_person_id": alice, "to_person_id": bob},
        ])
        assert r.status_code == 200
        r = client.get(f"/api/v1/duties/{duty1}/assignments", headers=admin_headers)
        assignments = [a for a in r.get_json()["data"] if a["date"] == "2026-06-07"]
        assert len(assignments) == 1
        assert assignments[0]["person_id"] == bob

    def test_cross_duty_swap(self, client, db, admin_headers):
        duty1, duty2, alice, bob = self.create_fixtures(client, admin_headers)
        self.assign(client, admin_headers, duty1, alice, "2026-06-07")
        self.assign(client, admin_headers, duty2, bob, "2026-06-07")
        r = self.swap(client, admin_headers, "2026-06-07", [
            {"duty_id": duty1, "from_person_id": alice, "to_person_id": bob},
            {"duty_id": duty2, "from_person_id": bob, "to_person_id": alice},
        ])
        assert r.status_code == 200
        r = client.get(f"/api/v1/duties/{duty1}/assignments", headers=admin_headers)
        a1 = [a for a in r.get_json()["data"] if a["date"] == "2026-06-07"][0]
        assert a1["person_id"] == bob
        r = client.get(f"/api/v1/duties/{duty2}/assignments", headers=admin_headers)
        a2 = [a for a in r.get_json()["data"] if a["date"] == "2026-06-07"][0]
        assert a2["person_id"] == alice

    def test_nonexistent_from_person(self, client, db, admin_headers):
        duty1, _, alice, bob = self.create_fixtures(client, admin_headers)
        r = self.swap(client, admin_headers, "2026-06-07", [
            {"duty_id": duty1, "from_person_id": 999, "to_person_id": bob},
        ])
        assert r.status_code == 404

    def test_conflict_to_person(self, client, db, admin_headers):
        duty1, _, alice, bob = self.create_fixtures(client, admin_headers)
        self.assign(client, admin_headers, duty1, alice, "2026-06-07")
        self.assign(client, admin_headers, duty1, bob, "2026-06-07")
        r = self.swap(client, admin_headers, "2026-06-07", [
            {"duty_id": duty1, "from_person_id": alice, "to_person_id": bob},
        ])
        assert r.status_code == 409

    def test_no_capability(self, client, db, auth_headers):
        r = self.swap(client, auth_headers, "2026-06-07", [
            {"duty_id": 1, "from_person_id": 1, "to_person_id": 2},
        ])
        assert r.status_code == 403

    def test_validation_error(self, client, db, admin_headers):
        r = client.post("/api/v1/assignments/swap", json={}, headers=admin_headers)
        assert r.status_code == 422

    def test_same_person_error(self, client, db, admin_headers):
        r = client.post("/api/v1/assignments/swap", json={
            "date": "2026-06-07",
            "changes": [{"duty_id": 1, "from_person_id": 1, "to_person_id": 1}],
        }, headers=admin_headers)
        assert r.status_code == 422
