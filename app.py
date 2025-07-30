import os
from google.cloud import speech
from google.auth.exceptions import DefaultCredentialsError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from database import db, User, Task, get_user_by_username, create_task, get_all_tasks, update_task, delete_task
from genai_parser import TaskParser
import click
import json
import google.oauth2.credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

#App & DB setup
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change this")

base_dir = os.path.abspath(os.path.dirname(__file__))
db_path  = os.path.join(base_dir, 'echo_note.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
print(app.config['SQLALCHEMY_DATABASE_URI'])

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
db.init_app(app)

@app.cli.command("init-db")
def init_db_command():
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    click.echo(f"Using database: {uri}")
    with app.app_context():
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
    links = [
        {'href': '/', 'text': 'Home', 'endpoint': 'index'},
        {'href': '/draw', 'text': 'Draw', 'endpoint': 'draw'},
        {'href': '/appearance', 'text': 'Appearance', 'endpoint': 'appearance'}
    ]
    
    # ✅ Only add if user hasn't connected Google yet
    if "credentials" not in session:
        links.append({'href': '/authorize', 'text': 'Connect Google Tasks', 'endpoint': 'authorize'})
    else:
        links.append({'href': '#', 'text': 'Google Connected', 'endpoint': ''})
    
    return links

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
        "accent": "#FCFCD", "textSecondary": "#ffffff", "buttonText": "#ffffff", "borderColor": "#444"
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
            
            if due_date and isinstance(due_date, str):
                due_date = due_date.strip().capitalize()
                
            print(f"Trying to save task: {task_text} (Due: {due_date})")
            if task_text:
                create_task(user_id=current_user.id, name=task_text, due_date=due_date, raw_text=transcript)
                count += 1
        db.session.commit()
        print(f"Saved {count} tasks to database")
        return jsonify(message=f'{count} tasks saved'), 200
    except Exception as e:
        print(f"Error saving tasks: {e}")
        return jsonify(error="Failed to save tasks"), 500
    
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
    success = delete_task(task_id)
    
    if success:
        return jsonify(message='Task deleted successfully'), 200
    else:
        return jsonify(error='Task not found'), 404

#route to prefill a google task event
@app.route("/api/prefill_gtask", methods=["POST"])
def prefill_gtask():
    data = request.get_json()
    raw_text = data.get("text", "")

    if not raw_text:
        return jsonify({"error": "Missing task text"}), 400

    parsed = task_parser.prefill_gtask(raw_text)

    if parsed and isinstance(parsed, list) and len(parsed) > 0:
        return jsonify(parsed[0])  # Just return the first parsed task
    else:
        return jsonify({"error": "No task extracted"}), 400

#route to prefill a google calendar event
@app.route("/api/prefill_gcalen", methods=["POST"])
def prefill_gcalen():
    data = request.get_json()
    raw_text = data.get("text", "")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    start_time = data.get("start_time", "")
    end_time = data.get("end_time", "")
    due_date = data.get("due_date", "")

    if not raw_text:
        return jsonify({"error": "Missing event text"}), 400

    parsed = task_parser.prefill_gcalen(raw_text, start_date, end_date, start_time, end_time, due_date)

    if parsed and isinstance(parsed, list) and len(parsed) > 0:
        return jsonify(parsed[0])  # Just return the first parsed task
    else:
        return jsonify({"error": "No event extracted"}), 400

SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar.events"
]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # For local dev without HTTPS

@app.route("/authorize")
def authorize():
    session.clear()

    # ✅ Debug: See what redirect URL is being generated
    generated_redirect = url_for("oauth2callback", _external=True)
    print("DEBUG: Generated redirect URI ->", generated_redirect)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": ["http://127.0.0.1:5000/oauth2callback"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=generated_redirect  # use what was generated
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": ["http://127.0.0.1:5000/oauth2callback"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=url_for("oauth2callback", _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }
    return redirect(url_for("index"))

def get_tasks_service():
    if "credentials" not in session:
        return None
    creds = google.oauth2.credentials.Credentials(**session["credentials"])
    return build("tasks", "v1", credentials=creds)

def get_calendar_service():
    if "credentials" not in session:
        return None
    creds = google.oauth2.credentials.Credentials(**session["credentials"])
    return build("calendar", "v3", credentials=creds)

@app.route("/api/google_task_create", methods=["POST"])
def google_task_create():
    service = get_tasks_service()
    if not service:
        return jsonify({"error": "Not authorized with Google"}), 401

    data = request.get_json()
    title = data.get("title")
    due_date = data.get("due_date")

    task_body = {"title": title}
    if due_date:
        task_body["due"] = f"{due_date}T00:00:00.000Z"  # Google expects RFC3339

    created_task = service.tasks().insert(tasklist='@default', body=task_body).execute()
    return jsonify(created_task)

@app.route("/api/google_event_create", methods=["POST"])
def google_event_create():
    service = get_calendar_service()
    if not service:
        return jsonify({"error": "Not authorized with Google"}), 401

    data = request.get_json()
    print("📌 Incoming event data:", data)

    tz_name = data.get("timezone", "UTC")

    def to_rfc3339(dt):
        if not dt:
            return None
        naive = datetime.fromisoformat(dt)
        return naive.replace(tzinfo=ZoneInfo(tz_name)).isoformat()

    start = to_rfc3339(data.get("start"))
    end = to_rfc3339(data.get("end"))

    if not start or not end:
        return jsonify({"error": "Missing start or end time"}), 400

    event = {
        "summary": data.get("title", "Untitled Event"),
        "description": data.get("description", ""),
        "start": {"dateTime": start, "timeZone": tz_name},
        "end": {"dateTime": end, "timeZone": tz_name}
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return jsonify(created_event)
