class TestAdmin:
    def test_list_auth_attempts_as_admin(self, client, db, admin_headers):
        r = client.get("/api/v1/admin/auth-attempts", headers=admin_headers)
        assert r.status_code == 200
        assert "data" in r.get_json()

    def test_list_auth_attempts_without_capability(self, client, db, auth_headers):
        r = client.get("/api/v1/admin/auth-attempts", headers=auth_headers)
        assert r.status_code == 403
