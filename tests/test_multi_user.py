import os
import tempfile
import pytest
import app as app_module
from app import app, db, task_parser
from database import User, Task

@pytest.fixture
def client(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        "WTF_CSRF_ENABLED": False,
    })
    # stub out speech client so no credentials needed
    class DummyClient:
        def recognize(self, *args, **kwargs):
            raise NotImplementedError
    monkeypatch.setattr(app_module, "speech_client", DummyClient())

    # create tables
    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()
    yield client

    # teardown
    try:
        os.remove(db_file)
    except OSError:
        pass

def test_register_login_logout_and_duplicate(client):
    # register
    rv = client.post("/sign_up", data={"username":"alice","password":"pwd"}, follow_redirects=True)
    assert rv.status_code == 200
    assert b"Account created" in rv.data

    # duplicate
    rv2 = client.post("/sign_up", data={"username":"alice","password":"pwd"})
    assert rv2.status_code == 200
    assert b"Username already taken" in rv2.data

    # login
    rv3 = client.post("/login", data={"username":"alice","password":"pwd"}, follow_redirects=True)
    assert rv3.status_code == 200
    assert b"Tasks" in rv3.data  # landed on home

    # logout
    rv4 = client.get("/logout", follow_redirects=True)
    assert rv4.status_code == 200
    assert b"Login" in rv4.data

def test_unauthorized_api_access(client):
    # without login, GET /api/tasks should redirect to /login
    rv = client.get("/api/tasks")
    assert rv.status_code == 302
    assert "/login" in rv.headers["Location"]

def test_task_isolation_between_two_users(client, monkeypatch):
    # make parse_transcript always return one task
    def fake_parse(text):
        return [{"text":"shared_task","due":None}]
    monkeypatch.setattr(task_parser, "parse_transcript", fake_parse)

    # user 1 checks
    c1 = client
    c1.post("/sign_up", data={"username":"u1","password":"p1"})
    c1.post("/login",    data={"username":"u1","password":"p1"})
    # save task
    resp = c1.post("/api/save_task", json={"transcript":"anything"})
    assert resp.status_code == 200
    assert "1 tasks saved" in resp.get_json()["message"]
    # list tasks
    tasks1 = c1.get("/api/tasks").get_json()
    assert len(tasks1) == 1
    assert tasks1[0]["name"] == "shared_task"
    # logout u1
    c1.get("/logout")

    # user 2 checks
    c2 = client
    c2.post("/sign_up", data={"username":"u2","password":"p2"})
    c2.post("/login",    data={"username":"u2","password":"p2"})
    # list tasks => empty
    tasks2 = c2.get("/api/tasks").get_json()
    assert tasks2 == []
    # save one for u2
    c2.post("/api/save_task", json={"transcript":"foo"})
    tasks2b = c2.get("/api/tasks").get_json()
    assert len(tasks2b) == 1
    assert tasks2b[0]["name"] == "shared_task"
    # logout u2
    c2.get("/logout")

    # login back as u1 and ensure still only 1
    c1.post("/login", data={"username":"u1","password":"p1"})
    tasks1_again = c1.get("/api/tasks").get_json()
    assert len(tasks1_again) == 1

def test_update_and_delete_permissions(client, monkeypatch):
    # stub parse_transcript again
    def fake_parse(text):
        return [{"text":"perm_task","due":None}]
    monkeypatch.setattr(task_parser, "parse_transcript", fake_parse)

    # user1 create
    c1 = client
    c1.post("/sign_up", data={"username":"a","password":"a"})
    c1.post("/login",    data={"username":"a","password":"a"})
    c1.post("/api/save_task", json={"transcript":"x"})
    tid = c1.get("/api/tasks").get_json()[0]["id"]
    c1.get("/logout")

    # user2 create and try to touch user1's
    c2 = client
    c2.post("/sign_up", data={"username":"b","password":"b"})
    c2.post("/login",    data={"username":"b","password":"b"})
    rv_up   = c2.put(f"/api/tasks/{tid}", json={"name":"nope"})
    rv_del  = c2.delete(f"/api/tasks/{tid}")
    assert rv_up.status_code  == 404
    assert rv_del.status_code == 404
    c2.get("/logout")

    # user1 can update & delete
    c1.post("/login", data={"username":"a","password":"a"})
    rv_up2  = c1.put(f"/api/tasks/{tid}", json={"name":"done","completed":True})
    assert rv_up2.status_code == 200
    upd = c1.get("/api/tasks").get_json()[0]
    assert upd["name"] == "done"

    rv_del2 = c1.delete(f"/api/tasks/{tid}")
    assert rv_del2.status_code == 200
    assert c1.get("/api/tasks").get_json() == []