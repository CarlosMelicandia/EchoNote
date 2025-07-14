import io
import pytest
from app import app, speech_client

class DummyResult:
    #a class with a class‐level transcript attribute so tests can read .transcript
    alternatives = [type('A', (object,), {'transcript': 'hello world'})]

class DummyResponse:
    #container with a .results list
    results = [DummyResult()]

@pytest.fixture(autouse=True)
def patch_speech(monkeypatch):
    #stub out the real SpeechClient.recognize method on import
    monkeypatch.setattr(
        speech_client,
        'recognize',
        lambda config, audio: DummyResponse()
    )

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_transcribe_success(client):
    data = {
        
        'audio': (io.BytesIO(b'\x00' * 1024), 'test.wav')
    }
    res = client.post(
        '/api/transcribe',
        data=data,
        content_type='multipart/form-data'
    )
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['transcript'] == 'hello world'
