from datetime import date, timedelta


class TestAutoAssign:
    MON = 0

    def monday(self, weeks_ahead=0):
        today = date.today()
        current = today - timedelta(days=today.weekday()) + timedelta(weeks=weeks_ahead)
        if current <= today:
            current += timedelta(weeks=1)
        return current

    def setup_group(self, client, admin_headers):
        r = client.post("/api/v1/duty-groups", json={
            "name": "Sunday Ushers", "day_of_week": self.MON,
        }, headers=admin_headers)
        assert r.status_code == 201, f"setup_group failed: {r.status_code} {r.get_json()}"
        return r.get_json()["data"]["id"]

    def add_duty(self, client, admin_headers, group_id, name, sort_order=0):
        r = client.post(f"/api/v1/duty-groups/{group_id}/duties", json={
            "name": name, "sort_order": sort_order,
        }, headers=admin_headers)
        assert r.status_code == 201, f"add_duty failed: {r.status_code} {r.get_json()}"
        return r.get_json()["data"]["id"]

    def add_person(self, client, admin_headers, first_name):
        r = client.post("/api/v1/persons", json={
            "first_name": first_name, "last_name": "X",
        }, headers=admin_headers)
        assert r.status_code == 201, f"add_person failed: {r.status_code} {r.get_json()}"
        return r.get_json()["data"]["id"]

    def add_membership(self, client, admin_headers, group_id, person_id, date_from):
        r = client.post(f"/api/v1/duty-groups/{group_id}/memberships", json={
            "person_id": person_id, "date_from": date_from,
        }, headers=admin_headers)
        assert r.status_code == 201, f"add_membership failed: {r.status_code} {r.get_json()}"
        return r

    def assign(self, client, admin_headers, duty_id, person_id, date_str):
        return client.post(f"/api/v1/duties/{duty_id}/assignments", json={
            "person_id": person_id, "date": date_str,
        }, headers=admin_headers)

    def auto_assign(self, client, headers, group_id, from_date, to_date=None):
        body = {"from_date": from_date}
        if to_date:
            body["to_date"] = to_date
        return client.post(f"/api/v1/duty-groups/{group_id}/auto-assign", json=body, headers=headers)

    def test_fills_all_duties(self, client, db, admin_headers):
        gid = self.setup_group(client, admin_headers)
        self.add_duty(client, admin_headers, gid, "Welcome", 0)
        self.add_duty(client, admin_headers, gid, "Sound", 1)
        alice = self.add_person(client, admin_headers, "Alice")
        bob = self.add_person(client, admin_headers, "Bob")
        self.add_membership(client, admin_headers, gid, alice, "2026-01-01")
        self.add_membership(client, admin_headers, gid, bob, "2026-01-01")
        m1 = str(self.monday(2))
        m2 = str(self.monday(3))
        r = self.auto_assign(client, admin_headers, gid, m1, m2)
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["gaps"] == []
        assert data["assignments_created"] == 4

    def test_respects_existing_assignments(self, client, db, admin_headers):
        gid = self.setup_group(client, admin_headers)
        d1 = self.add_duty(client, admin_headers, gid, "Welcome", 0)
        d2 = self.add_duty(client, admin_headers, gid, "Sound", 1)
        alice = self.add_person(client, admin_headers, "Alice")
        bob = self.add_person(client, admin_headers, "Bob")
        self.add_membership(client, admin_headers, gid, alice, "2026-01-01")
        self.add_membership(client, admin_headers, gid, bob, "2026-01-01")
        m1 = str(self.monday(2))
        self.assign(client, admin_headers, d1, alice, m1)
        r = self.auto_assign(client, admin_headers, gid, m1, m1)
        assert r.status_code == 201
        assert r.get_json()["data"]["assignments_created"] == 1
        r = client.get(f"/api/v1/duties/{d2}/assignments?date_from={m1}&date_to={m1}", headers=admin_headers)
        data = r.get_json()["data"]
        assert len(data) == 1
        assert data[0]["person_id"] == bob

    def test_rotation_across_dates(self, client, db, admin_headers):
        gid = self.setup_group(client, admin_headers)
        d1 = self.add_duty(client, admin_headers, gid, "Welcome", 0)
        self.add_duty(client, admin_headers, gid, "Sound", 1)
        alice = self.add_person(client, admin_headers, "Alice")
        bob = self.add_person(client, admin_headers, "Bob")
        charlie = self.add_person(client, admin_headers, "Charlie")
        self.add_membership(client, admin_headers, gid, alice, "2026-01-01")
        self.add_membership(client, admin_headers, gid, bob, "2026-01-01")
        self.add_membership(client, admin_headers, gid, charlie, "2026-01-01")
        m1 = str(self.monday(2))
        m2 = str(self.monday(4))
        self.auto_assign(client, admin_headers, gid, m1, m2)
        r = client.get(f"/api/v1/duties/{d1}/assignments", headers=admin_headers)
        welcome_assignments = r.get_json()["data"]
        persons_per_date = {a["date"]: a["person_id"] for a in welcome_assignments}
        ids = list(persons_per_date.values())
        assert len(set(ids)) > 1

    def test_gaps_when_not_enough_people(self, client, db, admin_headers):
        gid = self.setup_group(client, admin_headers)
        self.add_duty(client, admin_headers, gid, "Welcome", 0)
        self.add_duty(client, admin_headers, gid, "Sound", 1)
        self.add_duty(client, admin_headers, gid, "Tech", 2)
        alice = self.add_person(client, admin_headers, "Alice")
        self.add_membership(client, admin_headers, gid, alice, "2026-01-01")
        m1 = str(self.monday(2))
        r = self.auto_assign(client, admin_headers, gid, m1, m1)
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["assignments_created"] == 1
        assert len(data["gaps"]) == 1

    def test_skips_wrong_day_of_week(self, client, db, admin_headers):
        gid = self.setup_group(client, admin_headers)
        self.add_duty(client, admin_headers, gid, "Welcome", 0)
        alice = self.add_person(client, admin_headers, "Alice")
        self.add_membership(client, admin_headers, gid, alice, "2026-01-01")
        tuesday = str(self.monday(2) + timedelta(days=1))
        r = self.auto_assign(client, admin_headers, gid, tuesday, tuesday)
        assert r.status_code == 201
        assert r.get_json()["data"]["assignments_created"] == 0

    def test_no_capability(self, client, db, auth_headers):
        r = self.auto_assign(client, auth_headers, 1, "2026-06-07")
        assert r.status_code == 403

    def test_group_not_found(self, client, db, admin_headers):
        r = self.auto_assign(client, admin_headers, 999, "2026-06-07")
        assert r.status_code == 404
