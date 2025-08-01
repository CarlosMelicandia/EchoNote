import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
import re
from datetime import datetime, timedelta

#List of weekdays for date conversion
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


'''re = regular expressions ; cleans up text patterns --> when run w/o, output is messy. example below
"tasks": "```json\n[\n  {\n    \"text\": \"Finish the report\",\n   
 \"due\": \"Monday\"\n  },\n  {\n    \"text\": \"Email report to the team\",\n   
  \"due\": \"Monday\"\n  }\n]\n```"
'''

def get_date_from_due(due: str):
    """Convert a due date string to a datetime object."""
    if not due:
        return None
    
    due_lower = due.strip().lower()
    today = datetime.today()

    if due_lower == "today":
        return today.date().isoformat()
    if due_lower == "tomorrow":
        return (today + timedelta(days=1)).date().isoformat()
    if due_lower in WEEKDAYS:
        target_idx = WEEKDAYS.index(due_lower)
        delta = (target_idx - today.weekday() + 7) % 7
        if delta == 0:
            delta = 7  #next week if same day
        return (today + timedelta(days=delta)).date().isoformat()

    #If its already a proper date string (YYYY-MM-DD), return as is
    try:
        parsed = datetime.strptime(due, "%Y-%m-%d")
        return parsed.date().isoformat()
    except ValueError:
        return due  
    
class TaskParser:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv("GENAI_KEY")) 
        self.model = genai.GenerativeModel("gemini-1.5-pro") 

    def parse_transcript(self, transcript: str):
        base_directory = os.path.dirname(__file__)
        template = os.path.join(base_directory, "prompt_template.txt")
        with open(template, "r") as file:
            base_prompt = file.read()

        full_prompt = f"{base_prompt}\n\n{transcript}"

        try:
            response = self.model.generate_content(full_prompt)
            print("RAW GEMINI OUTPUT:")
            print(response.text)
            
            original = response.text.strip()
            clean_it = re.sub(r"```json|```", "", original).strip()
            tasks = json.loads(clean_it)
            print("Parsed tasks:", tasks)
            return tasks
        except Exception as e:
            print("Error parsing transcript:", e)
            print("Raw Gemini output:", response.text if 'response' in locals() else "None")
            return []
        
    def prefill_gtask(self, text):
        tasks = self.parse_transcript(text)
        for task in tasks:
            #fallback: if due is missing but start_date is present, set due to start_date
            if not task.get("due") and task.get("start_date"):
                task["due"] = task["start_date"]
            else:
                task["due"] = get_date_from_due(task.get("due"))
        return tasks

    def prefill_gcalen(self, text, start_date, end_date, start_time, end_time, due_date):
        """Prefill Google Calendar event with parsed tasks."""
        tasks = self.parse_transcript(text)
        enriched_tasks = []

        for task in tasks:
            due = task.get("due")
            converted_date = get_date_from_due(due)
            task["start_date"] = task.get("start_date") or converted_date
            task["end_date"] = task.get("end_date") or converted_date
            enriched_tasks.append(task)

        return enriched_tasks

'''class that reads a transcript and sends it to Gemini using a custom prompt.
returns a list of tasks based on what the user said. This lets us take 
unstructured voice input and turn it into structured to-do items for the project. testing
'''
