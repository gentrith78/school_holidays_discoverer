import os
import requests

from google import genai
from google.genai import types

class GeminiClient:
    """
    Minimal wrapper for Google Gemini API.
    """

    def __init__(self, model: str = "gemini-2.5-pro"):
        self.api_key = self.__read_api_key()
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_KEY"))

    def generate_with_gemini(self, prompt: str) -> str:
        # Combine prompt + text in the same message
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=prompt)
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=15000,
                    response_mime_type="application/json",
                ),
            )
            return resp.parts[0].text
        except Exception as e:
            print(f"[GeminiClient] Error: {e}")
            return ""

    def __read_api_key(self):
        return os.getenv("GEMINI_KEY")



