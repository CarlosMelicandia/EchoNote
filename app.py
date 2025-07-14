from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from genai_parser import TaskParser

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

parser = TaskParser()

@app.route('/api/parse-tasks', methods=['POST'])
def parse_tasks():
    data = request.get_json()
    transcript = data.get("transcript", "")

    if not transcript:
        return jsonify({"tasks": []})

    tasks = parser.parse_transcript(transcript)
    return jsonify({"tasks": tasks})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
