class TestAppSettings:
    def test_get_public_settings(self, client, db, auth_headers):
        r = client.get("/api/v1/settings", headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert isinstance(data, dict)

    def test_get_all_as_admin(self, client, db, admin_headers):
        r = client.get("/api/v1/settings", headers=admin_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        if "timezone" in data:
            assert data["timezone"] == "America/Chicago"

    def test_update_app_settings(self, client, db, admin_headers):
        r = client.patch(
            "/api/v1/settings",
            json={"timezone": "America/New_York", "default_calendar_view": "week"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["timezone"] == "America/New_York"
        assert data["default_calendar_view"] == "week"

    def test_update_app_settings_unauthorized(self, client, db, auth_headers):
        r = client.patch(
            "/api/v1/settings",
            json={"timezone": "America/Los_Angeles"},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_update_invalid_value(self, client, db, admin_headers):
        r = client.patch(
            "/api/v1/settings",
            json={"default_calendar_view": "invalid"},
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_update_unknown_key(self, client, db, admin_headers):
        r = client.patch(
            "/api/v1/settings",
            json={"bad_key": "value"},
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_update_page_size(self, client, db, admin_headers):
        r = client.patch(
            "/api/v1/settings",
            json={"default_page_size": "50"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["default_page_size"] == "50"

    def test_update_page_size_out_of_range(self, client, db, admin_headers):
        r = client.patch(
            "/api/v1/settings",
            json={"default_page_size": "999"},
            headers=admin_headers,
        )
        assert r.status_code == 422


class TestUserSettings:
    def test_get_empty(self, client, db, auth_headers):
        r = client.get("/api/v1/settings/user", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"] == {}

    def test_update(self, client, db, auth_headers):
        r = client.patch(
            "/api/v1/settings/user",
            json={"default_calendar_view": "agenda", "default_page_size": "25"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["default_calendar_view"] == "agenda"
        assert data["default_page_size"] == "25"

    def test_get_after_update(self, client, db, auth_headers):
        client.patch(
            "/api/v1/settings/user",
            json={"default_calendar_view": "week"},
            headers=auth_headers,
        )
        r = client.get("/api/v1/settings/user", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["default_calendar_view"] == "week"

    def test_settings_isolated(self, client, db, auth_headers, admin_headers):
        client.patch(
            "/api/v1/settings/user",
            json={"default_calendar_view": "month"},
            headers=auth_headers,
        )
        r = client.get("/api/v1/settings/user", headers=admin_headers)
        assert r.get_json()["data"] == {}

    def test_delete_by_null(self, client, db, auth_headers):
        client.patch(
            "/api/v1/settings/user",
            json={"default_calendar_view": "month"},
            headers=auth_headers,
        )
        r = client.patch(
            "/api/v1/settings/user",
            json={"default_calendar_view": None},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.get_json()["data"] == {}

    def test_invalid_value(self, client, db, auth_headers):
        r = client.patch(
            "/api/v1/settings/user",
            json={"default_calendar_view": "foo"},
            headers=auth_headers,
        )
        assert r.status_code == 422
