import os

import requests
from openai import OpenAI
client = OpenAI()


class OpenAiWebSearchClient:
    def __init__(self, openai_model: str = "gpt-5.1"):
        self.openai_model = openai_model
        self.timeout: int = 45
        self.openai_endpoint = "https://api.openai.com/v1/responses"

        self.session = requests.Session()
        self.openai_api_key = self._read_api_key_openai()

    def generate_with_open_ai_web_search(self, prompt):
        try:
            result = client.responses.create(
                model="gpt-5.1",
                input=prompt,
                reasoning={"effort": "medium"}, # todo change to medium if needed
                text={"verbosity": "low"},
                tools=[{"type": "web_search"}],  # <-- REQUIRED for web search
            )
            return result
        except:
            pass
        # payload = {
        #     "model": self.openai_model,
        #     "tools": [{"type": "web_search"}],
        #     "input": prompt
        # }
        #
        # headers = {
        #     "Content-Type": "application/json",
        #     "Authorization": f"Bearer {self.openai_api_key}"
        # }
        #
        # # response = requests.post(self.openai_endpoint, headers=headers, json=payload)
        #
        # if response.ok:
        #     data = response.json()
        #     for l in data["output"]:
        #         if l.get("type") == "message":
        #             for t in l.get("content"):
        #                 if t.get("text", None) is not None:
        #                     return t.get("text")
        #     return '{"holidays": [],"document_url": null}'
        # else:
        #     print("Error:", response.status_code, response.text)
        #     raise Exception(f"error processing with openai websearch: {response.status_code}, {response.text}")

    def _read_api_key_openai(self):
        return os.getenv("OPENAI_KEY")
