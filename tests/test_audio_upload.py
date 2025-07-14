import io
import pytest
from app import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    app.config['UPLOAD_FOLDER'] = tmp_path
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_upload_success(client):
    data = {
        
        'audio': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav')
    }
    res = client.post(
        '/api/upload',
        data=data,
        content_type='multipart/form-data'
    )
    assert res.status_code == 200
    json_data = res.get_json()
    # should echo back a "filename"
    assert 'filename' in json_data

    # and the file should actually be saved in UPLOAD_FOLDER
    saved = client.application.config['UPLOAD_FOLDER'] / json_data['filename']
    assert saved.exists()
