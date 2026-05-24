from tests.helpers import create_user


class TestIdempotency:
    def test_first_request_succeeds(self, app, client, db, admin_headers):
        r = client.post(
            "/api/v1/persons",
            json={"first_name": "Idem", "last_name": "Potent"},
            headers={
                **admin_headers,
                "Idempotency-Key": "test-key-1",
            },
        )
        assert r.status_code == 201
        assert "X-Idempotency-Replayed" not in r.headers

    def test_replay_returns_cached(self, app, client, db, admin_headers):
        headers = {**admin_headers, "Idempotency-Key": "replay-key"}
        r1 = client.post(
            "/api/v1/persons",
            json={"first_name": "Replay", "last_name": "Test"},
            headers=headers,
        )
        assert r1.status_code == 201
        r2 = client.post(
            "/api/v1/persons",
            json={"first_name": "Replay", "last_name": "Test"},
            headers=headers,
        )
        assert r2.status_code == 201
        assert r2.headers.get("X-Idempotency-Replayed") == "true"
        assert r2.get_json() == r1.get_json()

    def test_different_body_same_key(self, app, client, db, admin_headers):
        headers = {**admin_headers, "Idempotency-Key": "diff-key"}
        client.post(
            "/api/v1/persons",
            json={"first_name": "First", "last_name": "Try"},
            headers=headers,
        )
        r = client.post(
            "/api/v1/persons",
            json={"first_name": "Second", "last_name": "Try"},
            headers=headers,
        )
        assert r.status_code == 422
        assert r.get_json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSE"

    def test_missing_key_is_ignored(self, app, client, db, admin_headers):
        r = client.post(
            "/api/v1/persons",
            json={"first_name": "NoKey", "last_name": "Test"},
            headers=admin_headers,
        )
        assert r.status_code == 201
        assert "X-Idempotency-Replayed" not in r.headers

    def test_get_requests_ignored(self, app, client, db, auth_headers):
        client.post(
            "/api/v1/persons",
            json={"first_name": "GetTest", "last_name": "Test"},
            headers={**auth_headers, "Idempotency-Key": "get-key"},
        )
        r = client.get(
            "/api/v1/persons",
            headers={**auth_headers, "Idempotency-Key": "get-key"},
        )
        assert r.status_code == 200
