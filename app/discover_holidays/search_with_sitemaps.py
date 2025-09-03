import os
import logging
from typing import List
from pathlib import Path

import asyncio
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from app.ai_tools import gemini_client
from app.data_struc import School, Holiday
from app.ai_tools.gemini_client import GeminiClient
from app.discover_holidays.search_with_perplexity import HolidayDiscovererPerplexity

from usp.tree import sitemap_tree_for_homepage
from usp.web_client.requests_client import RequestsWebClient

class SearchWithSitemaps(GeminiClient):
    def __init__(self):
        GeminiClient.__init__(self)

        self.log = logging.getLogger("main_logger")

        self.max_sitemaps: int = 200

    def discover(self, school: School):
        self.log.info("Discovering Holidays through sitemap")
        sitemaps: List[str] = self._extract_sitemaps(school)[:self.max_sitemaps]

        if len(sitemaps) <= 1:
            return []

        candidates: List[str] = self._find_candidate_sitemaps(school, sitemaps)

        holidays = self._analyze_with_gemini(candidates, school)

        return holidays

    def _find_candidate_sitemaps(self, school: School, sitemaps: List[str]) -> List[str]:
        out: List[str] = []

        prompt = self._get_analyze_sitemaps_prompt(school, sitemaps)
        gemini_response = self.generate_with_gemini(prompt)
        parsed_gemini_response: dict = HolidayDiscovererPerplexity.parse_llm_json_obj(gemini_response)

        for el in parsed_gemini_response.get("selected", []):
            if el.get("confidence") > 85:
                out.append(el.get("sitemap_url", ""))

        return out

    def _analyze_with_gemini(self, sitemaps: List[str], school):
        holidays_out: List[Holiday] = []

        for url in sitemaps:
            site_content = asyncio.run(self._scrape_endpoint_async(url))
            analyze_content_prompt = self._get_analyze_site_content_prompt(school, url, site_content)
            gemini_output = self.generate_with_gemini(analyze_content_prompt)
            raw_holidays: dict = HolidayDiscovererPerplexity.parse_llm_json_obj(gemini_output)
            # todo add feature to get document link and analyze with gemini
            for item in raw_holidays.get("holidays"):
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
                        source_url=(item.get("source_url", "")),
                    ))
                except Exception:
                    continue


        return holidays_out

    async def _scrape_endpoint_async(self, url: str) -> str:
        self.log.info(f"scraping: {url}")
        browser_config = BrowserConfig(
            enable_stealth=True,  # Simple flag to enable
            # headless=False,
        )
        run_cfg = CrawlerRunConfig(
            excluded_tags=["nav", "footer"],
            wait_until="networkidle",
            scan_full_page=True
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url, config=run_cfg)
            return result.markdown

    def _extract_sitemaps(self, school: School) -> List[str]:
        out: List[str] = []
        """Fetches sitemap URLs and writes extracted endpoints to a file."""
        try:
            w_client = RequestsWebClient(verify=False)
            w_client.set_proxies({
            'server': f'{os.getenv("PROXY_HOST")}:{os.getenv("PROXY_PORT")}',
            'username': os.getenv("PROXY_USERNAME"),
            'password': os.getenv("PROXY_PASSWORD")
        })  # uncomment for proxy
            w_client.set_timeout(7)
            tree = sitemap_tree_for_homepage(school.website, web_client=w_client)

            out = []
            for page in tree.all_pages():
                url = page.url
                # if it's relative (starts with "/") or missing base, fix it
                if not url.startswith("http"):
                    url = urljoin(school.website, url)
                out.append(url)

            if len(out) > 1:
                return out

        except Exception as e:
            self.log.error(f"Error Extracting Sitemaps for: {school.website}")
            self.log.error(str(e))

        return out

    def _get_analyze_sitemaps_prompt(self, school: School, sitemaps: List[str]) -> str:
        prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                       .joinpath("gemini_analyze_sitemaps.txt"))

        with open(prompt_path.__str__(), "r") as f:
            prompt = f.read()

        prompt = (prompt.replace("<<school.lea_name>>", school.lea_name)
         .replace("<<school.state_name>>", school.state_name)
         .replace("<<school.country>>", school.country)
         .replace("<<site_root>>", school.website)
         .replace("<<sitemaps_list>>", str(sitemaps))
         )

        return prompt

    def _get_analyze_site_content_prompt(self, school: School, sitemap: str, page_content: str) -> str:
        prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                       .joinpath("gemini_analyze_site_content.txt"))

        with open(prompt_path.__str__(), "r") as f:
            prompt = f.read()

        prompt = (prompt.replace("<<school.lea_name>>", school.lea_name)
         .replace("<<school.state_name>>", school.state_name)
         .replace("<<school.country>>", school.country)
         .replace("<<site_root>>", school.website)
         .replace("<<page_url>>", sitemap)
         .replace("<<page_markdown>>", page_content)
         )

        return prompt

