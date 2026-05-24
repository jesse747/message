import io

from flask_jwt_extended import create_access_token
from tests.helpers import create_user


class TestListGroups:
    def test_list_success(self, client, db, auth_headers):
        r = client.get("/api/v1/groups", headers=auth_headers)
        assert r.status_code == 200

    def test_list_search(self, client, db, auth_headers, group_):
        r = client.get("/api/v1/groups?q=Test", headers=auth_headers)
        names = [g["name"] for g in r.get_json()["data"]]
        assert "Test Group" in names


class TestCreateGroup:
    def test_create_success(self, client, db, auth_headers):
        r = client.post("/api/v1/groups", json={"name": "My Group"}, headers=auth_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["name"] == "My Group"

    def test_create_validation_error(self, client, db, auth_headers):
        r = client.post("/api/v1/groups", json={}, headers=auth_headers)
        assert r.status_code == 422


class TestGetGroup:
    def test_get_success(self, client, db, auth_headers, group_):
        r = client.get(f"/api/v1/groups/{group_['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == group_["id"]


class TestUpdateGroup:
    def test_update_as_admin(self, client, db, admin_headers, group_):
        r = client.patch(f"/api/v1/groups/{group_['id']}", json={"description": "Updated"}, headers=admin_headers)
        assert r.status_code == 200

    def test_update_not_admin(self, client, db):
        owner_user = create_user(db, "owner", "owner@example.com")
        owner_token = create_access_token(identity=str(owner_user.id))
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        intruder_user = create_user(db, "intruder", "intruder@example.com")
        intruder_token = create_access_token(identity=str(intruder_user.id))
        intruder_headers = {"Authorization": f"Bearer {intruder_token}"}
        r = client.post("/api/v1/groups", json={"name": "Private Group"}, headers=owner_headers)
        group_id = r.get_json()["data"]["id"]
        r = c.patch(f"/api/v1/groups/{group_id}", json={"description": "Hack"}, headers=intruder_headers)
        assert r.status_code == 403


class TestDeleteGroup:
    def test_delete_success(self, client, db, admin_headers, group_):
        r = client.delete(f"/api/v1/groups/{group_['id']}", headers=admin_headers)
        assert r.status_code == 204


class TestGroupMembers:
    def test_add_member(self, client, db, admin_headers, group_, person):
        r = client.post(f"/api/v1/groups/{group_['id']}/members", json={"person_id": person["id"], "role": "member"}, headers=admin_headers)
        assert r.status_code == 201

    def test_add_duplicate_member(self, client, db, admin_headers, group_, person):
        client.post(f"/api/v1/groups/{group_['id']}/members", json={"person_id": person["id"]}, headers=admin_headers)
        r = client.post(f"/api/v1/groups/{group_['id']}/members", json={"person_id": person["id"]}, headers=admin_headers)
        assert r.status_code == 409

    def test_list_members(self, client, db, auth_headers, group_):
        r = client.get(f"/api/v1/groups/{group_['id']}/members", headers=auth_headers)
        assert r.status_code == 200

    def test_update_member_role(self, client, db, admin_headers, group_, person):
        client.post(f"/api/v1/groups/{group_['id']}/members", json={"person_id": person["id"], "role": "member"}, headers=admin_headers)
        r = client.patch(f"/api/v1/groups/{group_['id']}/members/{person['id']}", json={"role": "admin"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["role"] == "admin"

    def test_remove_member(self, client, db, admin_headers, group_, person):
        client.post(f"/api/v1/groups/{group_['id']}/members", json={"person_id": person["id"]}, headers=admin_headers)
        r = client.delete(f"/api/v1/groups/{group_['id']}/members/{person['id']}", headers=admin_headers)
        assert r.status_code == 204


class TestGroupMeetings:
    def test_create_meeting(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Group Meet", "day_of_week": 2, "frequency": "weekly",
        }, headers=admin_headers)
        assert r.status_code == 201
        assert "instances" in r.get_json()["data"]
        assert len(r.get_json()["data"]["instances"]) == 12

    def test_list_meetings(self, client, db, auth_headers, group_):
        r = client.get(f"/api/v1/groups/{group_['id']}/meetings", headers=auth_headers)
        assert r.status_code == 200

    def test_create_meeting_ignores_body_fks(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Group Meet", "day_of_week": 2, "team_id": 999, "group_id": 999,
        }, headers=admin_headers)
        assert r.status_code == 201

    def test_create_meeting_auto_generates_instances(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 3, "frequency": "weekly",
        }, headers=admin_headers)
        assert r.status_code == 201
        data = r.get_json()["data"]
        instances = data["instances"]
        assert len(instances) == 12
        for inst in instances:
            assert "id" in inst
            assert "date" in inst
            assert inst["cancelled"] is False


class TestMeetingInstances:
    def test_list_instances(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.get_json()["data"]) == 12

    def test_create_manual_instance(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances", json={
            "date": "2026-06-15", "time": "14:00",
        }, headers=admin_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["date"] == "2026-06-15"

    def test_generate_more_instances(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances", json={
            "generate": True, "count": 6,
        }, headers=admin_headers)
        assert r.status_code == 201
        assert len(r.get_json()["data"]) == 6

    def test_update_instance(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        inst_id = r.get_json()["data"]["instances"][0]["id"]
        r = client.patch(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}", json={
            "location": "Room 101", "notes": "Bring snacks",
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["location"] == "Room 101"
        assert r.get_json()["data"]["notes"] == "Bring snacks"

    def test_cancel_instance_creates_post(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        inst_id = r.get_json()["data"]["instances"][0]["id"]
        r = client.patch(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}", json={
            "cancelled": True, "cancellation_message": "Cancelled due to holiday",
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["cancelled"] is True
        assert data["cancellation_message"] == "Cancelled due to holiday"
        r = client.get(f"/api/v1/groups/{group_['id']}/posts", headers=admin_headers)
        posts = r.get_json()["data"]
        assert any("Cancelled due to holiday" in p["content"] for p in posts)

    def test_cancel_no_message(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        inst_id = r.get_json()["data"]["instances"][0]["id"]
        r = client.patch(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}", json={
            "cancelled": True,
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()["data"]["cancelled"] is True

    def test_delete_instance(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Weekly Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        inst_id = r.get_json()["data"]["instances"][0]["id"]
        r = client.delete(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}", headers=admin_headers)
        assert r.status_code == 204
        r = client.get(f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances", headers=admin_headers)
        assert len(r.get_json()["data"]) == 11


class TestMeetingInstanceFiles:
    def test_upload_and_list_files(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        inst_id = r.get_json()["data"]["instances"][0]["id"]
        data = {"file": (io.BytesIO(b"hello"), "test.txt")}
        r = client.post(
            f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}/files",
            data=data, headers=admin_headers, content_type="multipart/form-data",
        )
        assert r.status_code == 201
        r = client.get(
            f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}/files",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert len(r.get_json()["data"]) == 1

    def test_delete_file(self, client, db, admin_headers, group_):
        r = client.post(f"/api/v1/groups/{group_['id']}/meetings", json={
            "name": "Meet", "day_of_week": 1, "frequency": "weekly",
        }, headers=admin_headers)
        meeting_id = r.get_json()["data"]["id"]
        inst_id = r.get_json()["data"]["instances"][0]["id"]
        data = {"file": (io.BytesIO(b"data"), "doc.txt")}
        r = client.post(
            f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}/files",
            data=data, headers=admin_headers, content_type="multipart/form-data",
        )
        file_id = r.get_json()["data"][0]["id"]
        r = client.delete(
            f"/api/v1/groups/{group_['id']}/meetings/{meeting_id}/instances/{inst_id}/files/{file_id}",
            headers=admin_headers,
        )
        assert r.status_code == 204


class TestGroupPosts:
    def test_create_post(self, client, db, admin_headers, group_, person):
        r = client.post(f"/api/v1/groups/{group_['id']}/posts", json={"content": "Hello group!"}, headers=admin_headers)
        assert r.status_code == 201

    def test_list_posts(self, client, db, auth_headers, group_):
        r = client.get(f"/api/v1/groups/{group_['id']}/posts", headers=auth_headers)
        assert r.status_code == 200


class TestGroupJoinLeave:
    def test_join_public_group(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/groups", json={"name": "Public Group", "is_public": True}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/groups/{group_id}/join", headers=auth_headers)
        assert r.status_code == 201
        assert r.get_json()["data"]["role"] == "member"

    def test_join_private_group(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/groups", json={"name": "Private Group"}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/groups/{group_id}/join", headers=auth_headers)
        assert r.status_code == 403

    def test_join_duplicate(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/groups", json={"name": "Test Group", "is_public": True}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        client.post(f"/api/v1/groups/{group_id}/join", headers=auth_headers)
        r = client.post(f"/api/v1/groups/{group_id}/join", headers=auth_headers)
        assert r.status_code == 409

    def test_leave_group(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/groups", json={"name": "Test Group", "is_public": True}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        client.post(f"/api/v1/groups/{group_id}/join", headers=auth_headers)
        r = client.post(f"/api/v1/groups/{group_id}/leave", headers=auth_headers)
        assert r.status_code == 204

    def test_leave_not_member(self, client, db, admin_headers, auth_headers):
        r = client.post("/api/v1/groups", json={"name": "Test Group", "is_public": True}, headers=admin_headers)
        group_id = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/groups/{group_id}/leave", headers=auth_headers)
        assert r.status_code == 404
