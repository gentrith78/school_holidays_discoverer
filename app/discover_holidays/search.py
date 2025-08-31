# app/holiday_discovery/perplexity_discoverer.py
from __future__ import annotations

import os
import json
import re
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.data_struc import School, Holiday
from app.ai_tools.gemini_visual_client import GeminiVisualClient

class HolidayDiscovererPerplexity(GeminiVisualClient):
    """
    Minimal MVP: use Perplexity 'online' model to search the web and extract holidays
    for a given School (LEA/district). Returns a list[Holiday].

    Requirements:
      - env var PPLX_API_KEY or pass api_key explicitly
      - Perplexity model that supports web search
    """

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "sonar",
        timeout: int = 45,
    ):
        self.api_key = api_key or os.environ.get("PPLX_API_KEY")
        GeminiVisualClient.__init__(self)

        if not self.api_key:
            raise ValueError("Perplexity API key missing. Set PPLX_API_KEY or pass api_key.")
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()

    # ------------- public -------------
    def discover(self, school: School) -> List[Holiday]:
        """Fetch holidays for a School using Perplexity web search."""
        prompt = self._build_prompt(school)
        raw = self._call_perplexity(prompt)
        if not raw:
            return []

        # Perplexity returns text; try to parse JSON block from it
        obj = self.parse_llm_json_obj(raw) if raw else None


        holidays_out: List[Holiday] = []
        document_url: Optional[str] = None

        if obj and isinstance(obj, dict):
            document_url = (obj.get("document_url") or None) if isinstance(obj.get("document_url"), str) else None
            raw_holidays = obj.get("holidays") if isinstance(obj.get("holidays"), list) else []

            if not raw_holidays and not document_url.isspace() and not document_url == "" and document_url is not None:
                raw_holidays = self.extract_json_with_visual_gemini(document_url)

            for item in raw_holidays:
                if not isinstance(item, dict):
                    continue
                try:
                    holidays_out.append(Holiday(
                        academic_year=(item.get("academic_year") or "").strip(),
                        holiday_name=(item.get("holiday_name") or "").strip(),
                        category=(item.get("category") or "").strip(),
                        date_start=(item.get("date_start") or "").strip(),
                        date_end=(item.get("date_end") or "").strip(),
                        notes=(item.get("notes") or None),
                        source_url=((item.get("source_url") or "").strip() or None),
                    ))
                except Exception:
                    continue


        return holidays_out

    # ------------- internals -------------
    def _build_prompt(self, school: School) -> str:
        prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                       .joinpath("perplexity_discover_holidays.txt"))

        with open(prompt_path.__str__(), "r") as f:
            prompt = f.read()

        q_hint = f'{school.lea_name} {school.state_name} {school.country} school holiday dates calendar term dates academic year site:({school.website})' if school.website else f'{school.lea_name} {school.state_name} {school.country} school holiday dates calendar term dates'

        prompt = (prompt.replace("<<school.lea_name>>", school.lea_name)
                  .replace("<<school.state_name>>", school.state_name)
                  .replace("<<school.country>>", school.country)
                  .replace("<<school.website>>", school.website)
                  .replace("<<q_hint>>", q_hint)
                  )

        return prompt.strip()

    def _call_perplexity(self, prompt: str) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: Dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise extraction engine. Return only the requested JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1200,
            # "return_citations": True,
        }

        try:
            resp = self.session.post(self.API_URL, headers=headers, json=body, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # Perplexity-style response (OpenAI-compatible)
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Perplexity] error: {e}")
            return None

    @staticmethod
    def parse_llm_json_obj(text: str) -> Optional[Dict[str, Any]]:
        """
        Robustly parse a JSON OBJECT returned by an LLM.
        Expected shape: {"holidays": [...], "document_url": "https://..."}
        Accepts code fences, outer quotes, trailing commas, and truncation after last '}'.

        Returns dict or None.
        """
        if not text:
            return None

        t = text.strip()

        # Strip code fences
        if t.startswith("```"):
            t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE).strip()

        # Strip single outer quotes (common when printed or embedded)
        if (t.startswith("'") and t.endswith("'")) or (t.startswith('"') and t.endswith('"')):
            t = t[1:-1].strip()

        # First attempt
        try:
            obj = json.loads(t)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # Try to find the first '{' block and salvage until last '}'
        m = re.search(r"\{\s*.+", t, flags=re.DOTALL)
        if not m:
            return None

        obj_txt = m.group(0)
        last_brace = obj_txt.rfind("}")
        if last_brace != -1:
            obj_txt = obj_txt[: last_brace + 1]

        # Remove trailing commas like ", }" or ", ]"
        obj_txt = re.sub(r",\s*([}\]])", r"\1", obj_txt)

        try:
            obj = json.loads(obj_txt)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None