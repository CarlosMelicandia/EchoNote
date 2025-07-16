import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Task, create_task, get_all_tasks, update_task, delete_task

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture(autouse=True)
def override_session(monkeypatch, db_session):
    monkeypatch.setattr("database.SessionLocal", lambda: db_session)

def test_create_and_get_task():
    create_task("Write unit tests")
    tasks = get_all_tasks()
    assert len(tasks) == 1
    assert tasks[0].name == "Write unit tests"
    assert tasks[0].completed is False

def test_update_task():
    create_task("Initial name")
    updated = update_task(1, name="Updated name", completed=True)
    assert updated.name == "Updated name"
    assert updated.completed is True

def test_delete_task():
    create_task("Task to delete")
    deleted = delete_task(1)
    assert deleted is True
    tasks = get_all_tasks()
    assert len(tasks) == 0
