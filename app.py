import os
from google.cloud import speech
from google.auth.exceptions import DefaultCredentialsError
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from database import create_task, init_db, get_all_tasks, update_task, delete_task


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///echo_note.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
db = SQLAlchemy(app)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

# Dummy speech client class for testing


class DummySpeechClient:
    """adding so tests can import app.py without crashing"""

    def recognize(self, config, audio):
        # stub - tests will override this
        raise NotImplementedError("This should be monkey patched in tests")


# Initializing google speech client
try:
    speech_client = speech.SpeechClient()
except DefaultCredentialsError:
    # fallback to a stub so that tests can monkey patch
    speech_client = DummySpeechClient()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        note_content = request.form['content']
        new_note = Note(content=note_content)
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for('index'))

    notes = Note.query.all()
    return render_template('index.html', notes=notes)

# Audio upload route


@app.route('/api/upload', methods=['POST'])
def upload_audio():
    f = request.files.get('audio')
    if not f:
        return {"error": "no file"}, 40
    # sanitizing filename (used werkzeug helper)
    filename = secure_filename(f.filename)
    upload_folder = app.config['UPLOAD_FOLDER']
    # make sure the folder exists
    os.makedirs(upload_folder, exist_ok=True)
    # do we want to save audio to disk? if not we dont need next two lines
    save_path = os.path.join(upload_folder, filename)
    f.save(save_path)
    return {"filename": filename}, 200

# Audio transcribe route


@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify(error='no file'), 400
    audio_bytes = request.files['audio'].read()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        language_code="en-US",
    )
    resp = speech_client.recognize(config=config, audio=audio)
    # Join all of the results into one string
    transcript = " ".join(r.alternatives[0].transcript for r in resp.results)
    return jsonify(transcript=transcript), 200

# List tasks route

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    tasks = get_all_tasks()
    return jsonify([{
        "id": t.id,
        "name": t.name,
        "completed": t.completed
    } for t in tasks])

# process tasks route
@app.route('/api/save_task', methods=['POST'])
def save_task():
    data = request.get_json()
    print("Received JSON:", data)
    if not data or "tasks" not in data:
        print("❌ No tasks provided")
        return jsonify(error='Task name is required'), 400
    tasks = data["tasks"]
    count = 0
    for task_name in tasks:
        task_text = task_name.get("text")
        print("➡️ Trying to save task:", task_text)
        if task_text:
            create_task(task_text)
            count += 1
    print(f"✅ Saved {count} tasks to database")
    return jsonify(message=f'{count} tasks saved'), 200



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()#initialize the tasks database
    app.run(debug=True)
