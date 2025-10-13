import os
from typing import Dict, Optional

import requests

class PerplexityClient:
    def __init__(self, model: str = "sonar-pro"):
        self.model = model
        self.timeout: int = 45

        self.ppx_endpoint = "https://api.perplexity.ai/chat/completions"
        self.session = requests.Session()

    def generate_with_perplexity(self, prompt: str) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self._read_api_key_ppx()}",
            "Content-Type": "application/json",
        }
        body: Dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise extraction engine. Return only the requested JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 10000,
            # "return_citations": True,
        }

        try:
            resp = self.session.post(self.ppx_endpoint, headers=headers, json=body, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # Perplexity-style response (OpenAI-compatible)
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Perplexity] error: {e}")
            return None

    def _read_api_key_ppx(self):
        return os.getenv("PERPLEXITY_KEY")
