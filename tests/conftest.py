import os

import pytest
from flask_jwt_extended import create_access_token

from src.message import create_app
from src.message import db as _db
from tests.helpers import create_user


@pytest.fixture
def event_type(app, client, db, admin_headers):
    """Seed default event types and return the Baptism entry."""
    default_types = [
        "Baptism", "Confirmation", "First Communion", "Wedding", "Funeral",
        "Membership Started", "Transfer", "Child Dedication",
        "Profession of Faith", "Other",
    ]
    result = None
    for name in default_types:
        r = client.post(
            "/api/v1/event-types",
            json={"name": name, "sort_order": 0},
            headers=admin_headers,
        )
        if name == "Baptism":
            result = r.get_json()["data"]
    return result


@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "test"
    app = create_app("test")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def auth_headers(app, client, db):
    user = create_user(db, "testuser", "test@example.com")
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(app, client, db):
    user = create_user(db, "admin", "admin@example.com", is_super_admin=True)
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def person(app, client, db, admin_headers):
    r = client.post("/api/v1/persons", json={
        "first_name": "John", "last_name": "Doe",
        "email_personal": "john@example.com",
    }, headers=admin_headers)
    return r.get_json()["data"] if r.status_code == 201 else None


@pytest.fixture
def team(app, client, db, admin_headers):
    r = client.post("/api/v1/teams", json={"name": "Test Team"}, headers=admin_headers)
    return r.get_json()["data"] if r.status_code == 201 else None


@pytest.fixture
def group_(app, client, db, admin_headers):
    r = client.post("/api/v1/groups", json={"name": "Test Group"}, headers=admin_headers)
    return r.get_json()["data"] if r.status_code == 201 else None


@pytest.fixture
def flock(app, client, db, admin_headers):
    r = client.post("/api/v1/flocks", json={"name": "Test Flock"}, headers=admin_headers)
    return r.get_json()["data"] if r.status_code == 201 else None
