import io


class TestListPersons:
    def test_list_success(self, client, db, auth_headers):
        r = client.get("/api/v1/persons", headers=auth_headers)
        assert r.status_code == 200
        assert "data" in r.get_json()

    def test_list_search(self, client, db, auth_headers, person):
        r = client.get("/api/v1/persons?q=John", headers=auth_headers)
        assert r.status_code == 200
        names = [p["first_name"] for p in r.get_json()["data"]]
        assert "John" in names

    def test_list_pagination(self, client, db, auth_headers):
        r = client.get("/api/v1/persons?page=1&limit=5", headers=auth_headers)
        assert r.status_code == 200
        meta = r.get_json()["meta"]
        assert meta["page"] == 1
        assert meta["limit"] == 5


class TestCreatePerson:
    def test_create_success(self, client, db, admin_headers):
        r = client.post("/api/v1/persons", json={
            "first_name": "Jane", "last_name": "Smith",
        }, headers=admin_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["first_name"] == "Jane"

    def test_create_without_capability(self, client, db, auth_headers):
        r = client.post("/api/v1/persons", json={
            "first_name": "Jane", "last_name": "Smith",
        }, headers=auth_headers)
        assert r.status_code == 403

    def test_create_validation_error(self, client, db, admin_headers):
        r = client.post("/api/v1/persons", json={}, headers=admin_headers)
        assert r.status_code == 422


class TestGetPerson:
    def test_get_success(self, client, db, auth_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == person["id"]

    def test_get_not_found(self, client, db, auth_headers):
        r = client.get("/api/v1/persons/99999", headers=auth_headers)
        assert r.status_code == 404


class TestUpdatePerson:
    def test_update_success(self, client, db, admin_headers, person):
        r = client.patch(f"/api/v1/persons/{person['id']}", json={"first_name": "Johnny"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["first_name"] == "Johnny"

    def test_update_own_profile(self, client, db, auth_headers):
        r = client.get("/api/v1/auth/user", headers=auth_headers)
        user_id = r.get_json()["data"]["id"]
        # Find the person linked to this user (created during register)
        r = client.get("/api/v1/persons", headers=auth_headers, query_string={"q": "testuser"})
        persons = r.get_json()["data"]
        if persons:
            r = client.patch(f"/api/v1/persons/{persons[0]['id']}", json={"notes": "Updated own"}, headers=auth_headers)
            assert r.status_code == 200

    def test_update_own_profile_restricted(self, client, db, auth_headers):
        r = client.get("/api/v1/auth/user", headers=auth_headers)
        r = client.get("/api/v1/persons", headers=auth_headers, query_string={"q": "testuser"})
        persons = r.get_json()["data"]
        if persons:
            r = client.patch(
                f"/api/v1/persons/{persons[0]['id']}",
                json={"first_name": "Hacked"},
                headers=auth_headers,
            )
            assert r.status_code == 403


class TestDeletePerson:
    def test_delete_success(self, client, db, admin_headers, person):
        r = client.delete(f"/api/v1/persons/{person['id']}", headers=admin_headers)
        assert r.status_code == 204

    def test_delete_without_capability(self, client, db, auth_headers, person):
        r = client.delete(f"/api/v1/persons/{person['id']}", headers=auth_headers)
        assert r.status_code == 403


class TestPersonRelationships:
    def test_teams(self, client, db, auth_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}/teams", headers=auth_headers)
        assert r.status_code == 200

    def test_flocks(self, client, db, auth_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}/flocks", headers=auth_headers)
        assert r.status_code == 200

    def test_family(self, client, db, auth_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}/family", headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["id"] is None  # person has no family yet
        assert len(data["members"]) == 1
        assert data["members"][0]["role"] == "self"

    def test_groups(self, client, db, auth_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}/groups", headers=auth_headers)
        assert r.status_code == 200

    def test_relationships(self, client, db, auth_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}/relationships", headers=auth_headers)
        assert r.status_code == 200

    def test_memberships(self, client, db, auth_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}/memberships", headers=auth_headers)
        assert r.status_code == 200


class TestPersonPhoto:
    def test_upload_photo(self, client, db, admin_headers, person):
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        assert r.status_code == 201
        assert r.get_json()["data"]["photo_url"] is not None

    def test_upload_photo_requires_permission(self, client, db, auth_headers, person):
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**auth_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        assert r.status_code == 403

    def test_upload_no_file(self, client, db, admin_headers, person):
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data={},
        )
        assert r.status_code == 400

    def test_get_photo(self, client, db, admin_headers, person):
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        r = client.get(f"/api/v1/persons/{person['id']}/photo", headers=admin_headers)
        assert r.status_code == 200
        assert r.data == b"fake-image-data"

    def test_get_photo_no_photo(self, client, db, admin_headers, person):
        r = client.get(f"/api/v1/persons/{person['id']}/photo", headers=admin_headers)
        assert r.status_code == 404

    def test_delete_photo(self, client, db, admin_headers, person):
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        r = client.delete(f"/api/v1/persons/{person['id']}/photo", headers=admin_headers)
        assert r.status_code == 204
        r = client.get(f"/api/v1/persons/{person['id']}/photo", headers=admin_headers)
        assert r.status_code == 404

    def test_photo_url_in_detail(self, client, db, admin_headers, person):
        data = {"file": (io.BytesIO(b"fake-image-data"), "photo.jpg")}
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        r = client.get(f"/api/v1/persons/{person['id']}", headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["photo_url"] is not None

    def test_replace_photo(self, client, db, admin_headers, person):
        data = {"file": (io.BytesIO(b"first-image"), "photo.jpg")}
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        first_url = r.get_json()["data"]["photo_url"]

        data = {"file": (io.BytesIO(b"second-image"), "photo.jpg")}
        r = client.post(
            f"/api/v1/persons/{person['id']}/photo",
            headers={**admin_headers, "Content-Type": "multipart/form-data"},
            data=data,
        )
        second_url = r.get_json()["data"]["photo_url"]
        assert first_url != second_url

        r = client.get(f"/api/v1/persons/{person['id']}/photo", headers=admin_headers)
        assert r.data == b"second-image"


class TestPersonEvents:
    def test_list_events_empty(self, client, db, auth_headers, person, event_type):
        r = client.get(f"/api/v1/persons/{person['id']}/events", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"] == []

    def test_create_event_success(self, client, db, admin_headers, person, event_type):
        r = client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={
                "event_type_id": event_type["id"],
                "event_date": "2024-06-15",
                "location": "Main Church",
                "notes": "Test baptism",
            },
            headers=admin_headers,
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["event_type_id"] == event_type["id"]
        assert data["event_date"] == "2024-06-15"
        assert data["location"] == "Main Church"
        assert data["notes"] == "Test baptism"
        assert data["event_type"] == "Baptism"

    def test_create_event_without_capability(self, client, db, auth_headers, person, event_type):
        r = client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={"event_type_id": event_type["id"], "event_date": "2024-01-01"},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_create_event_bad_event_type(self, client, db, admin_headers, person):
        r = client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={"event_type_id": 99999, "event_date": "2024-01-01"},
            headers=admin_headers,
        )
        assert r.status_code == 404

    def test_create_event_validation_error(self, client, db, admin_headers, person):
        r = client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={},
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_list_events(self, client, db, admin_headers, person, event_type):
        client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={"event_type_id": event_type["id"], "event_date": "2024-01-01"},
            headers=admin_headers,
        )
        r = client.get(f"/api/v1/persons/{person['id']}/events", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.get_json()["data"]) == 1

    def test_get_event(self, client, db, admin_headers, person, event_type):
        r = client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={"event_type_id": event_type["id"], "event_date": "2024-03-20"},
            headers=admin_headers,
        )
        eid = r.get_json()["data"]["id"]
        r = client.get(
            f"/api/v1/persons/{person['id']}/events/{eid}", headers=admin_headers
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["event_date"] == "2024-03-20"

    def test_get_event_not_found(self, client, db, admin_headers, person):
        r = client.get(
            f"/api/v1/persons/{person['id']}/events/99999", headers=admin_headers
        )
        assert r.status_code == 404

    def test_update_event(self, client, db, admin_headers, person, event_type):
        r = client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={"event_type_id": event_type["id"], "event_date": "2024-04-10"},
            headers=admin_headers,
        )
        eid = r.get_json()["data"]["id"]
        r = client.patch(
            f"/api/v1/persons/{person['id']}/events/{eid}",
            json={"location": "Updated Location", "notes": "Updated notes"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["location"] == "Updated Location"
        assert data["notes"] == "Updated notes"

    def test_delete_event(self, client, db, admin_headers, person, event_type):
        r = client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={"event_type_id": event_type["id"], "event_date": "2024-05-05"},
            headers=admin_headers,
        )
        eid = r.get_json()["data"]["id"]
        r = client.delete(
            f"/api/v1/persons/{person['id']}/events/{eid}", headers=admin_headers
        )
        assert r.status_code == 204
        r = client.get(
            f"/api/v1/persons/{person['id']}/events/{eid}", headers=admin_headers
        )
        assert r.status_code == 404

    def test_person_detail_includes_events(self, client, db, admin_headers, person, event_type):
        client.post(
            f"/api/v1/persons/{person['id']}/events",
            json={"event_type_id": event_type["id"], "event_date": "2024-01-01"},
            headers=admin_headers,
        )
        r = client.get(f"/api/v1/persons/{person['id']}", headers=admin_headers)
        assert r.status_code == 200
        events = r.get_json()["data"]["events"]
        assert len(events) >= 1
        assert events[0]["event_type"] == "Baptism"
