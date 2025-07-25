import os
from google.cloud import speech
from google.auth.exceptions import DefaultCredentialsError
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify
from database import db, create_task, get_all_tasks, update_task, delete_task
from genai_parser import TaskParser
task_parser = TaskParser()

app = Flask(__name__)
#"sqlite:///./echo_note.db"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///echo_note.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
db.init_app(app)

# Dummy speech client class for testing
class DummySpeechClient:
    """adding so tests can import app.py without crashing"""
    def recognize(self, config, audio):
        # stub - tests will override this
        raise NotImplementedError("This should be monkey patched in tests")
    
#protect app from calling dummy stub when we aren't testing
if os.getenv("FLASK_ENV") == "testing":
    speech_client = DummySpeechClient()
else:
    # Initializing google speech client
    speech_client = speech.SpeechClient()

#verify which client 
print("speech_client is", type(speech_client).__name__)

# Define nav links to be used across routes
def get_nav_links():
    return [
        {'href': '/', 'text': 'Home', 'endpoint': 'index'},
        {'href': '/draw', 'text': 'Draw', 'endpoint': 'draw'},
        {'href': '/appearance', 'text': 'Appearance', 'endpoint': 'appearance'}
    ]

#updated to use Task model not Note model
@app.route('/', methods=['GET'])
def index():
    tasks = get_all_tasks()
    return render_template('index.html', tasks=tasks, nav_links=get_nav_links())

@app.route('/draw', methods=['GET'])
def draw():
    return render_template('draw.html', nav_links=get_nav_links())

# Audio upload route
@app.route('/api/upload', methods=['POST'])
def upload_audio():
    f = request.files.get('audio')
    if not f:
        return {"error": "no file"}, 400
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
    try:
        if 'audio' not in request.files:
            return jsonify(error='no file'), 400
        audio_bytes = request.files['audio'].read()
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            language_code="en-US",
        )
        resp = speech_client.recognize(config=config, audio=audio)
        transcript = " ".join(r.alternatives[0].transcript for r in resp.results)
        return jsonify(transcript=transcript), 200
    except NotImplementedError as e:
        return jsonify(error=str(e)), 501
    except Exception as e:
        return jsonify(error="Transcription failed"), 500

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
    try:
        data = request.get_json()
        print("Received JSON:", data)

        if not data or "transcript" not in data:
            print("No transcript provided")
            return jsonify(error='Transcript is required'), 400

        transcript = data["transcript"]
        parsed_tasks = task_parser.parse_transcript(transcript)

        if not isinstance(parsed_tasks, list):
            return jsonify(error="Failed to parse tasks"), 500
        
        count = 0
        for task_data in parsed_tasks:
            task_text = task_data.get("text")
            due_date = task_data.get("due")
            print(f"Trying to save task: {task_text} (Due: {due_date})")
            if task_text:
                create_task(task_text, due_date)
                count += 1   
        print(f"Saved {count} tasks to database")
        return jsonify(message=f'{count} tasks saved'), 200
    
    except NotImplementedError as e:
        return jsonify(error=str(e)), 501
    
    except Exception as e:
        return jsonify(error="Save task failed"), 500
    

@app.route('/appearance', methods=['GET'])
def appearance():
    return render_template('appearance.html', nav_links=get_nav_links())

# Update task route
@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task_route(task_id):
    data = request.get_json()
    
    if not data:
        return jsonify(error='No data provided'), 400
    
    name = data.get('name')
    completed = data.get('completed')
    
    updated_task = update_task(task_id, name, completed)
    
    if updated_task:
        return jsonify(message='Task updated successfully'), 200
    else:
        return jsonify(error='Task not found'), 404

# Delete task route
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task_route(task_id):
    success = delete_task(task_id)
    
    if success:
        return jsonify(message='Task deleted successfully'), 200
    else:
        return jsonify(error='Task not found'), 404

@app.route("/api/parse_task", methods=["POST"])
def parse_task():
    data = request.get_json()
    raw_text = data.get("text", "")

    if not raw_text:
        return jsonify({"error": "Missing task text"}), 400

    parsed = task_parser.parse_transcript(raw_text)

    if parsed and isinstance(parsed, list) and len(parsed) > 0:
        return jsonify(parsed[0])  # Just return the first parsed task
    else:
        return jsonify({"error": "No task extracted"}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()#initialize the tasks database
    app.run(debug=True)