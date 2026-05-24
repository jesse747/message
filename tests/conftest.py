import os
import pytest
from flask_jwt_extended import create_access_token
from src.message import create_app, db as _db
from src.message.models import Person, User, Team, Group, Flock
from tests.helpers import create_user


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
