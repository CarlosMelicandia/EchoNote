import os
from dotenv import load_dotenv
import google.generativeai as genai

class TaskParser:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv("GENAI_KEY")) 
        self.model = genai.GenerativeModel("gemini-1.5-flash") 

    def parse_transcript(self, transcript: str):
        with open("prompt_template.txt", "r") as file:
            base_prompt = file.read()

        full_prompt = f"{base_prompt}\n\n{transcript}"

        try:
            response = self.model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            print("Error parsing transcript:", e)
            return "[]"

'''class that reads a transcript and sends it to Gemini using a custom prompt.
returns a list of tasks based on what the user said. This lets us take 
unstructured voice input and turn it into structured to-do items for the project.
'''