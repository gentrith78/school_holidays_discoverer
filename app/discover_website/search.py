# app/discovery/website_discoverer_llm.py
from __future__ import annotations
import os
import requests
from urllib.parse import urlparse
from typing import Dict, List, Optional
import urllib.parse

from app.data_struc import School

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

    def discover(self, school: School) -> Dict:
        """Return dict with chosen website, confidence, and candidates."""

        query = f'"{school.lea_name}" {school.state_name} {school.country} official site'
        candidates = self._serp_search(query)

        # limit to top N
        candidates = candidates[: self.max_candidates]

        # fetch page snippets
        enriched = []
        for c in candidates:
            snippet = self._fetch_snippet(c["url"])
            enriched.append({
                "url": c["url"],
                "title": c.get("title", ""),
                "snippet": c.get("snippet", ""),
                "content": snippet,
            })

        # ask LLM to choose
        llm_choice = self._ask_llm(enriched, school)

        return {
            "website": llm_choice.get("website"),
            "confidence": llm_choice.get("confidence", 0),
            "candidates": enriched,
        }

    # --- internals ---

    def _serp_search(self, query: str) -> List[Dict]:
        headers = {"Authorization": f"Bearer {self.serp_api_key}",
                   "Content-Type": "application/json"
                   }

        query = urllib.parse.quote_plus(query)

        payload = {
            "zone": "serp_api1", # todo ask for this and change key
            "url": f"https://www.google.com/search?q={query}",
            "format": "raw"
        }

        try:
            resp = self.session.post(self.BRIGHTDATA_ENDPOINT, headers=headers, json=payload, timeout=self.request_timeout)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"SERP error: {e}")
            return []

        return self._parse_google_results(html)

    @staticmethod
    def _parse_google_results(html: str):
        """
        Parse raw Google HTML into [{url, title, snippet}, ...].
        """
        from lxml import html as lxml_html

        results = []
        try:
            doc = lxml_html.fromstring(html)
            # Google result blocks
            for g in doc.xpath('//div[@class="g"]'):
                link = g.xpath('.//a/@href')
                title = g.xpath('.//h3/text()')
                snippet = g.xpath('.//span[@class="aCOpRe"]/text()')
                if link and title:
                    results.append({
                        "url": link[0],
                        "title": title[0],
                        "snippet": " ".join(snippet) if snippet else ""
                    })
        except Exception as e:
            print(f"[SERP parser] failed: {e}")

        return results

    def _fetch_snippet(self, url: str, max_chars: int = 1500) -> str:
        try:
            r = self.session.get(url, timeout=self.request_timeout, verify=False, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            text = r.text
            return text[:max_chars].replace("\n", " ")
        except Exception:
            return ""

    def _ask_llm(self, candidates: List[Dict], school: School) -> Dict:
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

        # call LLM client (Gemini/OpenAI/etc.)
        response = self.llm_client.generate(prompt)
        try:
            return response.json()
        except Exception:
            return {"website": None, "confidence": 0}
