import json
import pytest
from werkzeug.security import generate_password_hash
from app import app, db
from database import User

@pytest.fixture
def client():
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    # Recreate schema and default user
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            username="user1",
            pw_hash=generate_password_hash("pass1", method="pbkdf2:sha256")
        )
        db.session.add(user)
        db.session.commit()

    # Create test client and log in
    client = app.test_client()
    login_resp = client.post(
        "/login",
        data={"username": "user1", "password": "pass1"},
        follow_redirects=True
    )
    assert login_resp.status_code == 200
    return client

def test_save_and_list_tasks(client):
    # Save a new task via transcript
    resp = client.post(
        "/api/save_task",
        json={"transcript": "Finish math homework tomorrow"}
    )
    assert resp.status_code == 200

    # List tasks and verify
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    tasks = resp.get_json()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Finish math homework"
    assert tasks[0]["completed"] is False

def test_update_and_delete_task(client):
    # Create one
    client.post("/api/save_task", json={"transcript": "Write report"})
    tasks = client.get("/api/tasks").get_json()
    task_id = tasks[0]["id"]

    # Update it
    resp = client.put(
        f"/api/tasks/{task_id}",
        json={"name": "Write final report", "completed": True}
    )
    assert resp.status_code == 200

    # Confirm update
    tasks = client.get("/api/tasks").get_json()
    assert tasks[0]["name"] == "Write final report"
    assert tasks[0]["completed"] is True

    # Delete it
    resp = client.delete(f"/api/tasks/{task_id}")
    assert resp.status_code == 200

    # Confirm deletion
    tasks = client.get("/api/tasks").get_json()
    assert tasks == []

def test_register_and_login_flow():
    c = app.test_client()
    # Ensure new db for this flow
    with app.app_context():
        db.drop_all()
        db.create_all()

    # Register
    resp = c.post(
        "/sign_up",
        data={"username": "newuser", "password": "newpass"},
        follow_redirects=True
    )
    assert resp.status_code == 200

    # Now log in as that user
    resp = c.post(
        "/login",
        data={"username": "newuser", "password": "newpass"},
        follow_redirects=True
    )
    assert resp.status_code == 200

    # Access protected endpoint
    resp = c.get("/", follow_redirects=False)
    assert resp.status_code == 200
