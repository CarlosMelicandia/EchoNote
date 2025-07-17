# EchoNote – Voice-Powered Task Manager

EchoNote is a Python-based web app that uses Google Speech-to-Text and Google Gemini AI to turn spoken input into organized tasks. Just speak your to-do list, and EchoNote will transcribe, extract, and save your tasks.

## General Info

This project was developed as part of the SEO Tech Developers Summer 2025 program. It demonstrates how to:

- Use speech recognition to capture user input
- Parse natural language into structured data using AI
- Store and display tasks using a local database and Flask app

## Technologies

This project uses:

- Python 3.11+
- Flask
- SQLite + SQLAlchemy
- Google Cloud Speech-to-Text API
- Google Generative AI (Gemini)
- HTML/CSS (Jinja templates)

## Setup Instructions

1. Clone this repo  
   `git clone git@github.com:CarlosMelicandia/EchoNote.git`

2. Go into the folder  
   `cd EchoNote`

3. Set up your virtual environment  
   ```bash
   python3 -m venv .venv  
   source .venv/bin/activate  
   pip install -r requirements.txt
   
4. Add your Google credentials JSON to:
./sensitive-credentials/echonote-api-key.json

5. Set environment variables in the terminal:
export GOOGLE_APPLICATION_CREDENTIALS="./sensitive-credentials/echonote-api-key.json"  
export FLASK_ENV=development

6. Run the app
python3 app.py
Then go to http://localhost:5000 in your browser.

## Contact
- Carlos Melicandia – c.melicandia15@gmail.com
- Demi Fashemo – dfashemo@seas.upenn.edu
- Mofetoluwa Samadelus – mofetoluwa.samadelus@morehouse.edu
- Eshaal Syeda – eshaal.syeda@richmond.edu
