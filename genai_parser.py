import os
import google.generativeai as genai
from dotenv import load_dotenv

class TaskParser:
    def __init__(self):
        load_dotenv() #loads API key from .env -> i think anyone who wants to run this needs to have their own api ke
        api_key = os.getenv("GENAI_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def parse_transcript(self, transcript):
        with open("prompt_template.txt", "r") as file:
            base_prompt = file.read()

        full_prompt = f"{base_prompt}\n\n{transcript}"

        try:
            response = self.model.generate_content(full_prompt)
            tasks = eval(response.text.strip())  #converts Gemini’s response into Python data works if returns a Python-style list
        except Exception as e:
            print("Gemini Error:", e)
            tasks = []

        return tasks

'''class that reads a transcript and sends it to Gemini using a custom prompt.
returns a list of tasks based on what the user said. This lets us take 
unstructured voice input and turn it into structured to-do items for the project.
'''