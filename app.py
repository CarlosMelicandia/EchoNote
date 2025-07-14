from google.cloud import speech
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#Initializing google speech client
speech_client = speech.SpeechClient()

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

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

#Audio transcribe route
@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify(error='no file'), 400
    audio_bytes = request.files['audio'].read()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16, 
        sample_rate_hertz = 16000,
        language_code = "en-US",
    )
    resp = speech_client.recognize(config=config, audio=audio)
    #Join all results into one string
    transcript = " ".join(r.alternatives[0].transcript for r in resp.results)
    return jsonify(transcript=transcript), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
