import os
import json
import base64
import logging
import tempfile
from typing import Any

import requests
from google import genai
from pypdf import PdfReader
from google.genai import types

from app.data_struc import School
from app.utils import parse_llm_json_obj
from app.ai_tools.utils.doc_extractor import docx_to_markdown
from app.ai_tools.fetch_prompts import get_gemini_visual_prompt
from app.ai_tools.gemini_client import GeminiClient
from app.ai_tools.fetch_prompts import get_analyze_site_content_prompt



def _guess_mime(path: str) -> str:
    p = path.lower()
    if p.endswith(".pdf"):  return "application/pdf"
    if p.endswith(".png"):  return "image/png"
    if p.endswith(".jpg") or p.endswith(".jpeg"): return "image/jpeg"
    if p.endswith(".webp"): return "image/webp"
    return "application/octet-stream"

class GeminiVisualClient:
    """
    Analyzes images and pdf files and outputs results based on the prompt...
    Minimal client to send a PDF/image to Gemini and get back:
      - raw text (extract_text)
      - JSON (extract_json)
    """

    def __init__(self, gemini_model: str = "gemini-2.5-pro", timeout: int = 60):
        self.api_key_gemini = self._read_api_key_gemini()
        self.gemini_model = gemini_model
        self.timeout = timeout
        self.max_doc_pages: int = 20
        self.log = logging.getLogger("main_logger")
        self.client = genai.Client(api_key=os.environ.get("GEMINI_KEY"))
        self.gemini_text_model = GeminiClient()
        # self.prompt = get_gemini_visual_prompt()

        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        self.session = requests.Session()
        self.session.proxies = {
        'http': f'http://{os.getenv("PROXY_USERNAME")}:{os.getenv("PROXY_PASSWORD")}@{os.getenv("PROXY_HOST")}:{os.getenv("PROXY_PORT")}',
        'https': f'http://{os.getenv("PROXY_USERNAME")}:{os.getenv("PROXY_PASSWORD")}@{os.getenv("PROXY_HOST")}:{os.getenv("PROXY_PORT")}'
        }

    def generate_json_with_visual_gemini(self, url: str, school: School) -> Any:
        """
        Returns parsed JSON (dict/list) extracted by the model from the file.
        If model returns invalid JSON, this will raise json.JSONDecodeError.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(url)[-1]) as tmp:
                r = self.session.get(url, timeout=self.timeout, verify=False)

                tmp.write(r.content)
                tmp.flush()
                tmp_path = tmp.name  # save path before context exits
                # count pages
                if self.count_pages(tmp_path) > self.max_doc_pages:
                    self.log.info("Too Document Many pages on document")
                    return []

                r.raise_for_status()

                if tmp_path.endswith(".docx"):
                    return self._extract_from_doxc(tmp_path)
                else:
                    raw_response = self._send(tmp_path, school,response_mime_type="application/json")
                    parsed = parse_llm_json_obj(raw_response)
                    if parsed is None:
                        parsed = json.loads(raw_response)
                if parsed is None:
                    raise
                return parsed
        except Exception as e:
            print(str(e))
            self.log.error(f"Error Getting data from visual gemini, Error Message: {str(e)}")
            return []

    # --------- Internals ---------
    def _send(self, file_path: str, school: School, response_mime_type: str) -> str:
        """
        returns response from gemini
        """
        user_prompt = get_gemini_visual_prompt(school)

        with open(file_path, "rb") as f:
            file_bytes = f.read()
        # Upload the file once (2 GB/file; kept ~48h)

        resp = self.client.models.generate_content(
            model=self.gemini_model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=user_prompt),
                        types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                    ],
                )
            ],
            # Use the typed config (replaces generation_config)
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=20000,
                response_mime_type="application/json"
            ),
        )
        return resp.parts[0].text

    def _extract_from_doxc(self, file_path: str):
        md_coverted_text = docx_to_markdown(file_path)

        # dummy school:
        d_s = School(
            country="",
            state_name="",
            region_city="",
            lea_name="",
            website=""
        )
        prompt = get_analyze_site_content_prompt(d_s, "", md_coverted_text)
        prompt = prompt.replace("LEA/District: <<school.lea_name>>", "")
        prompt = prompt.replace("State/Region: <<school.state_name>>", "")
        prompt = prompt.replace("Country: <<school.country>>", "")
        prompt = prompt.replace("<<page_url>>", "Not Available")
        prompt = prompt.replace("<<site_root>>", "Not Available")

        raw_response = self.gemini_text_model.generate_with_gemini(prompt)

        return parse_llm_json_obj(raw_response).get("holidays", [])

    def _read_api_key_gemini(self):
        return os.getenv("GEMINI_KEY")

    @staticmethod
    def count_pages(tmp_path: str) -> int:
        if tmp_path.lower().endswith(".pdf"):
            reader = PdfReader(tmp_path)
            return len(reader.pages)

        return 1 # just return a number lower than self.max_doc_pages since it may be an image or other doc type...

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    uu = "https://www.eufaulacityschools.org/site/handlers/filedownload.ashx?moduleinstanceid=2232&dataid=5225&FileName=2025-2026%20Calendar%20Approved%2002.18.2025.pdf"

    a  = GeminiVisualClient()

    a.generate_json_with_visual_gemini(uu)

    #######################################
    # import os
    # from dotenv import load_dotenv
    # load_dotenv()
    # fn = "/Users/gentrithoxhaj/Desktop/SchoolWebsiteHolidaysScraper/ASD20 2025-26 Annual Calendar (1).pdf"
    #
    # from google import genai
    #
    # client = genai.Client(api_key=os.environ.get("GEMINI_KEY"))
    #
    # # Upload the file once (2 GB/file; kept ~48h)
    # pdf = client.files.upload(file=fn)
    #
    # # Use the uploaded file directly in contents
    # resp = client.models.generate_content(
    #     model="gemini-2.5-flash",
    #     contents=[
    #         "Extract all holidays and term dates from this school and output them as json",
    #         pdf,  # <- the uploaded file
    #     ],
    #     # Optional generation settings:
    #     config={"temperature": 0.1, "max_output_tokens": 10000}
    # )
    # print(resp.text)
    # # todo add this type of gemini integration to all ai tools with gemini
    #
