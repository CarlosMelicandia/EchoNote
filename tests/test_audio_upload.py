import io
import pytest
from app import app
from database import db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client(tmp_path):
    #Test config: test mode, in‑memory DB, and tmp_path for uploads
    app.config.update({
        'TESTING': True,
        'UPLOAD_FOLDER': tmp_path,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    #Recreate schema & seed a single user
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            username='user1',
            pw_hash=generate_password_hash('pass1', method='pbkdf2:sha256')
        )
        db.session.add(user)
        db.session.commit()

    #Return a test client
    with app.test_client() as c:
        yield c

def test_upload_success(client):
    # login first so @login_required passes
    login = client.post(
        '/login',
        data={'username': 'user1', 'password': 'pass1'},
        follow_redirects=True
    )
    assert login.status_code == 200

    # do the upload
    data = {
        'audio': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav')
    }
    res = client.post(
        '/api/upload',
        data=data,
        content_type='multipart/form-data'
    )

    assert res.status_code == 200
    body = res.get_json()
    assert 'filename' in body

    # file really landed in the tmp_path folder
    saved = client.application.config['UPLOAD_FOLDER'] / body['filename']
    assert saved.exists()
