class TestRelationships:
    def test_create_relationship(self, client, db, admin_headers):
        r1 = client.post("/api/v1/persons", json={"first_name": "Parent", "last_name": "A"}, headers=admin_headers)
        r2 = client.post("/api/v1/persons", json={"first_name": "Child", "last_name": "A"}, headers=admin_headers)
        p1 = r1.get_json()["data"]["id"]
        p2 = r2.get_json()["data"]["id"]
        r = client.post(
            "/api/v1/relationships",
            json={"person_1_id": p1, "person_2_id": p2, "relationship_type": "parent"},
            headers=admin_headers,
        )
        assert r.status_code == 201
        assert r.get_json()["data"]["relationship_type"] == "parent"

    def test_create_duplicate(self, client, db, admin_headers):
        r1 = client.post("/api/v1/persons", json={"first_name": "X", "last_name": "Y"}, headers=admin_headers)
        r2 = client.post("/api/v1/persons", json={"first_name": "Z", "last_name": "Y"}, headers=admin_headers)
        p1 = r1.get_json()["data"]["id"]
        p2 = r2.get_json()["data"]["id"]
        client.post("/api/v1/relationships", json={"person_1_id": p1, "person_2_id": p2, "relationship_type": "spouse"}, headers=admin_headers)
        r = client.post("/api/v1/relationships", json={"person_1_id": p1, "person_2_id": p2, "relationship_type": "spouse"}, headers=admin_headers)
        assert r.status_code == 409

    def test_create_self_relationship(self, client, db, admin_headers, person):
        pid = person["id"]
        r = client.post("/api/v1/relationships", json={"person_1_id": pid, "person_2_id": pid, "relationship_type": "spouse"}, headers=admin_headers)
        assert r.status_code == 422

    def test_list_relationships(self, client, db, auth_headers):
        r = client.get("/api/v1/relationships", headers=auth_headers)
        assert r.status_code == 200

    def test_get_relationship(self, client, db, admin_headers):
        r1 = client.post("/api/v1/persons", json={"first_name": "A", "last_name": "B"}, headers=admin_headers)
        r2 = client.post("/api/v1/persons", json={"first_name": "C", "last_name": "B"}, headers=admin_headers)
        p1 = r1.get_json()["data"]["id"]
        p2 = r2.get_json()["data"]["id"]
        r = client.post("/api/v1/relationships", json={"person_1_id": p1, "person_2_id": p2, "relationship_type": "sibling"}, headers=admin_headers)
        rel_id = r.get_json()["data"]["id"]
        r = client.get(f"/api/v1/relationships/{rel_id}", headers=admin_headers)
        assert r.status_code == 200

    def test_delete_relationship(self, client, db, admin_headers):
        r1 = client.post("/api/v1/persons", json={"first_name": "D", "last_name": "E"}, headers=admin_headers)
        r2 = client.post("/api/v1/persons", json={"first_name": "F", "last_name": "E"}, headers=admin_headers)
        p1 = r1.get_json()["data"]["id"]
        p2 = r2.get_json()["data"]["id"]
        r = client.post("/api/v1/relationships", json={"person_1_id": p1, "person_2_id": p2, "relationship_type": "sibling"}, headers=admin_headers)
        rel_id = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/relationships/{rel_id}", headers=admin_headers)
        assert r.status_code == 204
