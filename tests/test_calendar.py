class TestCalendar:
    def test_calendar_with_params(self, client, db, auth_headers):
        r = client.get(
            "/api/v1/calendar?date_from=2026-06-01&date_to=2026-06-30",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.get_json()
        assert "data" in body
        assert "meta" in body
        assert "has_more" in body["meta"]

    def test_calendar_missing_params(self, client, db, auth_headers):
        r = client.get("/api/v1/calendar", headers=auth_headers)
        assert r.status_code == 400

    def test_calendar_events_only(self, client, db, auth_headers):
        r = client.get(
            "/api/v1/calendar?date_from=2026-06-01&date_to=2026-06-30&sources=events",
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_calendar_meetings_only(self, client, db, auth_headers):
        r = client.get(
            "/api/v1/calendar?date_from=2026-06-01&date_to=2026-06-30&sources=meetings",
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_calendar_birthdays_only(self, client, db, auth_headers):
        r = client.get(
            "/api/v1/calendar?date_from=2026-06-01&date_to=2026-06-30&sources=birthdays",
            headers=auth_headers,
        )
        assert r.status_code == 200
