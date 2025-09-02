import os
import json
import requests
from typing import Dict

class GeminiClient:
    """
    Minimal wrapper for Google Gemini API.
    """

    def __init__(self, model: str = "gemini-1.5-flash"):
        self.api_key = self.__read_api_key()
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.session = requests.Session()

    def generate_with_gemini(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return parsed JSON if possible.
        """
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        body = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 10000
            }
        }

        try:
            resp = self.session.post(self.endpoint, headers=headers, params=params, json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"[GeminiClient] Error: {e}")
            return ""

    def __read_api_key(self):
        return os.getenv("GEMINI_KEY")



