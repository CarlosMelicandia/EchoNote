from flask import Flask, request, jsonify
from genai_parser import TaskParser

app = Flask(__name__)
parser = TaskParser()

@app.route('/api/parse-tasks', methods=['POST'])
def parse_tasks():
    data = request.get_json()
    transcript = data.get("transcript", "")

#errors keep coming --> put this to solve
#if transcript empty, return empty list
    if not transcript:
        return jsonify({"tasks": []})

#calls the ai to read transcript and extract tasks
#jsonify(...): Sends the extracted tasks back as JSON
    tasks = parser.parse_transcript(transcript)
    return jsonify({"tasks": tasks})

if __name__ == "__main__":
    app.run(debug=True)