import io
import pytest

from app import app, speech_client
from database import db, User, Task
from werkzeug.security import generate_password_hash

class DummyResult:
    """a class with a class-level transcript attribute so tests can read .transcript"""
    alternatives = [type('A', (object,), {'transcript': 'hello world'})]

class DummyResponse:
    """container with a .results list"""
    results = [DummyResult()]

@pytest.fixture(autouse=True)
def patch_speech(monkeypatch):
    """Monkey-patch the real SpeechClient.recognize so it always returns our DummyResponse."""
    monkeypatch.setattr(
        speech_client,
        'recognize',
        lambda config, audio: DummyResponse()
    )

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    #create tables and valid user
    with app.app_context():
        db.create_all()
        test_user = User(
            username="user1",
            pw_hash=generate_password_hash("pass1", method="pbkdf2:sha256")
        )
        db.session.add(test_user)
        db.session.commit()

    #yield a test client that’s already wired up
    with app.test_client() as c:
        yield c

def test_transcribe_success(client):
    # first log in
    rv = client.post(
        '/login',
        data={'username': 'user1', 'password': 'pass1'},
        follow_redirects=True
    )
    assert rv.status_code == 200

    # send a dummy audio blob
    data = {
        'audio': (io.BytesIO(b'\x00' * 1024), 'test.wav')
    }
    res = client.post(
        '/api/transcribe',
        data=data,
        content_type='multipart/form-data'
    )

    assert res.status_code == 200
    payload = res.get_json()
    assert payload['transcript'] == 'hello world'
