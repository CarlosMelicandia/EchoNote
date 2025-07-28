import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
import re

'''re = regular expressions ; cleans up text patterns --> when run w/o, output is messy. example below
"tasks": "```json\n[\n  {\n    \"text\": \"Finish the report\",\n   
 \"due\": \"Monday\"\n  },\n  {\n    \"text\": \"Email report to the team\",\n   
  \"due\": \"Monday\"\n  }\n]\n```"
'''

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

'''class that reads a transcript and sends it to Gemini using a custom prompt.
returns a list of tasks based on what the user said. This lets us take 
unstructured voice input and turn it into structured to-do items for the project. testing
'''