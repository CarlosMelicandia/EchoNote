import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

class TaskParser:
    def __init__(self):
        load_dotenv()
        genai.api_key = os.getenv("GENAI_KEY")

        self.client = genai.Client(api_key=genai.api_key)
        self.model_name = "gemini-1.5-flash"
        self.system_instruction = "You are an assistant that extracts tasks from transcripts."

    def parse_transcript(self, transcript: str):
        with open("prompt_template.txt", "r") as file:
            base_prompt = file.read()

        full_prompt = f"{base_prompt}\n\n{transcript}"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                ),
                contents=full_prompt,
            )
            return response.text.strip()
        except Exception as e:
            print("Error parsing transcript:", e)
            return "[]"
            
'''class that reads a transcript and sends it to Gemini using a custom prompt.
returns a list of tasks based on what the user said. This lets us take 
unstructured voice input and turn it into structured to-do items for the project.
'''