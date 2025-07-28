import pytest
from flask import Flask
from database import db, User, Task, create_task, get_all_tasks, update_task, delete_task

@pytest.fixture(scope="function")
def app():
    app = Flask(__name__)
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app

@pytest.fixture(scope="function")
def session(app):
    return db.session

def make_user(session, username="tester"):
    """Helper to create & return a User so tasks can refer to it."""
    u = User(username=username, pw_hash="fakehash")
    session.add(u)
    session.commit()
    return u

def test_create_and_get_task(app, session):
    user = make_user(session)
    t = create_task(user.id, "Write unit tests")
    tasks = get_all_tasks(user.id)
    assert len(tasks) == 1
    assert tasks[0].name == "Write unit tests"
    assert tasks[0].completed is False

def test_update_task(app, session):
    user = make_user(session, username="updater")
    t = create_task(user.id, "Initial name")
    updated = update_task(t.id, name="Updated name", completed=True)
    assert updated.name == "Updated name"
    assert updated.completed is True

def test_delete_task(app, session):
    user = make_user(session, username="deleter")
    t = create_task(user.id, "Task to delete")
    deleted = delete_task(t.id)
    assert deleted is True
    # after deletion, get_all_tasks should be empty
    assert get_all_tasks(user.id) == []
