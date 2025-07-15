from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

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

@app.route('/draw')
def draw():
    return render_template('draw.html')

# Use a context_processor to avoid repeating
@app.context_processor
def inject_nav_links():
    return {
        "nav_links": [
            {"href": "/", "text": "Home"},
            {"href": "/draw", "text": "Draw"}
        ]
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
