# app/discovery/website_discoverer_llm.py
from __future__ import annotations

import os
import json
import logging
import requests
from urllib.parse import urlparse
from typing import Dict, List, Optional, reveal_type
import urllib.parse

from app.data_struc import School
from app.discover_holidays.search import HolidayDiscovererPerplexity

class WebsiteDiscovererLLM:
    """
    MVP approach: use SERP API to collect candidate URLs,
    fetch minimal text from top N,
    then let an LLM decide which is the official site.
    """

    BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"

    def __init__(
        self,
        serp_api_key: str,
        llm_client,
        max_candidates: int = 5,
        request_timeout: int = 12,
    ):
        self.serp_api_key = serp_api_key
        self.llm_client = llm_client
        self.max_candidates = max_candidates
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.log = logging.getLogger("main_logger")

    def discover(self, school: School) -> str:
        """Return dict with chosen website, confidence, and candidates."""

        query = f'"{school.lea_name}" {school.state_name} {school.country} official site'
        candidates = self._serp_search(query)

        # fetch page snippets
        enriched = []
        for c in candidates:
            snippet = self._fetch_snippet(c["link"])
            enriched.append({
                "url": c["link"],
                "title": c.get("title", ""),
                "snippet": c.get("description", ""),
                "content": snippet,
            })

        # ask LLM to choose
        llm_choice = self._ask_llm(enriched, school)

        self.log.info(f"Website Discovered: {str(llm_choice)}")

        if llm_choice.get("confidence", 0) >= 80:
            return llm_choice.get("website", "")

        return ""


    # --- internals ---

    def _serp_search(self, query: str) -> List[Dict]:
        out: List[dict] = []
        headers = {"Authorization": f"Bearer {self.serp_api_key}",
                   "Content-Type": "application/json"
                   }

        query = urllib.parse.quote_plus(query)

        payload = {
            "zone": "serp_api_lir",
            "url": f"https://www.google.com/search?q={query}&brd_json=1",
            "format": "json"
        }

        try:
            resp = self.session.post(self.BRIGHTDATA_ENDPOINT, headers=headers, json=payload, timeout=self.request_timeout)
            resp.raise_for_status()
            serialised_resp = json.loads(resp.json()['body'])
        except Exception as e:
            print(f"SERP error: {e}")
            return []

        for el in serialised_resp.get("organic", ""):
            out.append(
                {
                    "link": el.get("link", ""),
                    "title": el.get("title", ""),
                    "description": el.get("description"),
                }
            )

        return out



    def _fetch_snippet(self, url: str, max_chars: int = 1500) -> str:
        try:
            r = self.session.get(url, timeout=self.request_timeout, verify=False, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            text = r.text
            return text[:max_chars].replace("\n", " ")
        except Exception:
            return ""

    def _ask_llm(self, candidates: List[Dict], school: School) -> dict:
        # build prompt
        prompt = f"""
You are helping identify the OFFICIAL website of a school district / LEA.

LEA Name: {school.lea_name}
State/Region: {school.state_name}
Country: {school.country}

Here are candidate websites from search:

"""
        for idx, c in enumerate(candidates, 1):
            prompt += f"""
Candidate {idx}:
URL: {c['url']}
Title: {c['title']}
Snippet: {c['snippet']}
Content: {c['content'][:400]}...
"""

        prompt += """
Which candidate is most likely the official website of this LEA?
Respond in JSON with keys: {"website": URL, "confidence": number(0-100)}.
"""

        response: str = self.llm_client.generate(prompt)
        try:
            return HolidayDiscovererPerplexity.parse_llm_json_obj(response)
        except Exception:
            return {"website": None, "confidence": 0}
