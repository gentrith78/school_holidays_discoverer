# gemini_doc_client.py
import base64
import json
import os
import requests
import tempfile
from typing import Any, Optional
from pathlib import Path


def _guess_mime(path: str) -> str:
    p = path.lower()
    if p.endswith(".pdf"):  return "application/pdf"
    if p.endswith(".png"):  return "image/png"
    if p.endswith(".jpg") or p.endswith(".jpeg"): return "image/jpeg"
    if p.endswith(".webp"): return "image/webp"
    return "application/octet-stream"

class GeminiVisualClient:
    """
    Minimal client to send a PDF/image to Gemini 1.5 and get back:
      - raw text (extract_text)
      - JSON (extract_json)
    """

    def __init__(self, gemini_model: str = "gemini-1.5-pro", timeout: int = 60):
        self.api_key_gemini = self._read_api_key()
        self.gemini_model = gemini_model
        self.timeout = timeout
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        self.prompt = self._get_prompt()
        self.session = requests.Session()


    def extract_json_with_visual_gemini(self, url: str) -> Any:
        """
        Returns parsed JSON (dict/list) extracted by the model from the file.
        If model returns invalid JSON, this will raise json.JSONDecodeError.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(url)[-1]) as tmp:
                r = self.session.get(url, timeout=self.timeout)
                r.raise_for_status()
                tmp.write(r.content)
                tmp.flush()
                tmp_path = tmp.name  # save path before context exits

                raw_json = self._send(tmp.name, response_mime_type="application/json")

                return raw_json
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    # --------- Internals ---------
    def _send(self, file_path: str, *, response_mime_type: str) -> dict:
        """
        returns serialized json response from gemini
        """
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        mime = _guess_mime(file_path)
        user_prompt = self.prompt.strip() or "Extract the readable text from this document/image."

        body = {
            "contents": [{
                "parts": [
                    {"text": user_prompt},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
                "response_mime_type": response_mime_type
            }
        }

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key_gemini}

        r = self.session.post(self.endpoint, headers=headers, params=params, json=body, timeout=self.timeout)
        r.raise_for_status()

        return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])

    @staticmethod
    def _unwrap_text(api_response: dict) -> str:
        """
        Safely unwrap Gemini response text.
        """
        try:
            return api_response["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            # Fallback to empty string if shape changes
            return ""

    def _get_prompt(self) -> str:
        prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                       .joinpath("gemini_extract_dates_from_visual.txt"))

        with open(prompt_path.__str__(), "r") as f:
            prompt = f.read()

        return prompt

    def _read_api_key(self):
        return os.getenv("GEMINI_KEY")
