import os
from google.cloud import speech
from google.auth.exceptions import DefaultCredentialsError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import db, User, Task, get_user_by_username, create_task
from genai_parser import TaskParser
import click
import json

#App & DB setup
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change this")

base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'echo_note.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
print(app.config['SQLALCHEMY_DATABASE_URI'])

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
db.init_app(app)
@app.cli.command("init-db")
def init_db_command():
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    click.echo(f"Using database: {uri}")
    db.create_all()
    click.echo("Initialized the database")

#set up login manager
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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


# Define task parser & nav links to be used across routes
task_parser = TaskParser()

def get_nav_links():
    return [
        {'href': '/', 'text': 'Home', 'endpoint': 'index'},
        {'href': '/draw', 'text': 'Draw', 'endpoint': 'draw'},
        {'href': '/appearance', 'text': 'Appearance', 'endpoint': 'appearance'}
    ]

#Routes

#User authentication routes
#register route
@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Username already taken", "error")
        else:
            new_user = User(username=username, pw_hash=generate_password_hash(password, method="pbkdf2:sha256"))
            db.session.add(new_user)
            db.session.commit()
            flash("Account created - please log in", "success")
            return redirect(url_for("login"))
    return render_template("signup.html", nav_links=get_nav_links())

#login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_user_by_username(username)
        if user and check_password_hash(user.pw_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid credentials", "error")
    return render_template("login.html", nav_links=get_nav_links())

#logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


#Page routes
@app.route('/', methods=['GET'])
@login_required
def index():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    return render_template('index.html', tasks=tasks, nav_links=get_nav_links())

@app.route('/draw', methods=['GET'])
@login_required
def draw():
    return render_template('draw.html', nav_links=get_nav_links())

@app.route('/appearance', methods=['GET'])
@login_required
def appearance():
    return render_template('appearance.html', nav_links=get_nav_links(), user_theme=current_user.theme or {})

@app.route('/api/save_theme', methods=['POST'])
@login_required
def save_theme():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify(error="Invalid theme data"), 400
    current_user.theme = json.dumps(data)
    db.session.commit()
    return jsonify(message="Theme saved"), 200

@app.route('/api/get_theme', methods=['GET'])
@login_required
def get_theme():
    user_theme = current_user.get_theme()
    if user_theme:
        return jsonify(user_theme), 200
    default = {
        "bgPrimary": "#212121", "bgSecondary": "#303030", "textPrimary": "#ececf1",
        "accent": "#FCFCD", "textSecondary": "#ffffff", "buttonText": "#36395A", "borderColor": "#444"
    }
    return jsonify(default), 200

#Audio upload & transcription routes
# Audio upload route
@app.route('/api/upload', methods=['POST'])
@login_required
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
    return jsonify(filename=filename), 200

# Audio transcribe route
@app.route('/api/transcribe', methods=['POST'])
@login_required
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


#API task crud routes
# List tasks route
@app.route('/api/tasks', methods=['GET'])
@login_required
def list_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id':t.id,'name':t.name,'completed':t.completed} for t in tasks])

# process tasks route
@app.route('/api/save_task', methods=['POST'])
@login_required
def save_task():
    data = request.get_json() or {}
    if 'transcript' not in data:
        return jsonify(error="Transcript required"), 400

    parsed = task_parser.parse_transcript(data['transcript'])
    if not isinstance(parsed, list):
        return jsonify(error="Failed to parse tasks"), 500

    created = 0
    for item in parsed:
        txt = item.get("text")
        due = item.get("due")
        if txt:
            create_task(current_user.id, txt, due_date=due)
            #t = Task(user_id=current_user.id, name=txt, due_date=due)
            #db.session.add(t)
            created += 1
    db.session.commit()
    return jsonify(message=f"{created} tasks saved"), 200
    
# Update task route
@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task_route(task_id):
    data = request.get_json() or {}
    t = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not t:
        return jsonify(error="Not found"), 404
    t.name      = data.get('name', t.name)
    t.completed = data.get('completed', t.completed)
    db.session.commit()
    return jsonify(message="Updated"), 200

# Delete task route
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task_route(task_id):
    t = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not t:
        return jsonify(error="Not found"), 404
    db.session.delete(t); db.session.commit()
    return jsonify(message="Deleted"), 200
