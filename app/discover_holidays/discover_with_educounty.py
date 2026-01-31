"""
EduCounty.net Holiday Discovery Module

How it works:
1. Build search URL (cleaned LEA name) -> that page lists school pages.
2. find_calendar_url: scrape the search page, parse it to get the school page URL (no Gemini).
3. Scrape the school page (term dates are in HTML there) and call Gemini with
   get_analyze_site_content_prompt to extract holidays (same as SERP flow).
"""

import os
import re
import html
import logging
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.scraping_tools.brightdata_browser_scraper import scrape_html_from_wss, html_to_md_markdownify
from app.scraping_tools.crawl4ai_scraper import scrape_with_crwal4ai
from app.data_struc import School, Holiday
from app.ai_tools import (
    GeminiClient,
    GeminiVisualClient,
    get_analyze_site_content_prompt,
    get_match_school_result_prompt,
)
from app.ai_tools.gemini_client import GeminiClient as GeminiClientImpl
from app.utils import parse_llm_json_obj


# Words to strip from LEA name when building the search query (they worsen results)
LEA_SEARCH_STOP_WORDS = {"school", "schools", "district"}

EDUCOUNTY_BASE = "https://www.educounty.net"


class DiscoverWithEduCounty(GeminiClient, GeminiVisualClient):
    """
    Search URL shows school pages -> find school page URL from search -> scrape school page
    -> extract holidays from HTML with get_analyze_site_content_prompt + Gemini (same as SERP).
    """

    EDUCOUNTY_SEARCH_URL = "https://www.educounty.net/?s="

    def __init__(self):
        GeminiClient.__init__(self)
        GeminiVisualClient.__init__(self)
        self.log = logging.getLogger("main_logger")
        self.wss_endpoint = os.environ.get("BROWSER_WSS")
        self._flash_client = GeminiClientImpl(model="gemini-2.5-flash")

    def discover(self, school: School) -> List[Holiday]:
        """
        Build search URL -> find school page URL from search (no Gemini) -> get holidays from school page (Gemini).
        """
        self.log.info(f"Discovering holidays through EduCounty for {school.lea_name}")


        school_page_url = self.find_calendar_url(school)
        if school_page_url is None:
            # --- Add your own logic here if no school page URL was found ---
            self.log.info("No school page URL found for this school")
            return []

        # School page has term dates in HTML; we scrape it and use Gemini only here (same as last version)
        return self._get_holidays(school, school_page_url)

    @staticmethod
    def _clean_lea_name_for_search(lea_name: str) -> str:
        """
        Remove words that worsen search results (e.g. 'school', 'schools', 'district')
        and normalize whitespace.
        """
        if not lea_name or not lea_name.strip():
            return lea_name
        words = lea_name.strip().split()
        cleaned = [w for w in words if w.lower() not in LEA_SEARCH_STOP_WORDS]
        return " ".join(cleaned).strip() if cleaned else lea_name.strip()

    def _build_educounty_url(self, school: School) -> str:
        """Build the educounty.net search URL using only the filtered LEA name (no state, county, etc.)."""
        cleaned_lea = self._clean_lea_name_for_search(school.lea_name)
        if not cleaned_lea:
            return ""
        url = self.EDUCOUNTY_SEARCH_URL + quote_plus(cleaned_lea)
        self.log.info(f"EduCounty search URL: {url}")
        return url

    def find_calendar_url(self, school: School) -> Optional[str]:
        """
        Find the school page URL from the search results page.
        Scrapes the search page as HTML (return_md=False) so we can parse <main>/<article>.
        """
        search_url = self._build_educounty_url(school)
        if not search_url:
            return None

        if not self.wss_endpoint:
            return None

        # Return raw HTML so _parse_school_page_url_from_search can find <article> elements
        page_content = scrape_with_crwal4ai(search_url)
        if not page_content:
            return None


        # Parse search page: extract link to the school page (no Gemini)
        return self._parse_school_page_url_from_search(page_content, school, search_url)

    def _parse_school_page_url_from_search(
        self, page_content: str, school: School, search_url: str
    ) -> Optional[str]:
        """
        Parse the search results HTML: find <main> and each <article>, extract state,
        result name and URL. Use Gemini 2.5 Flash to decide if each result is the same
        school (handles messy names). Return the first matching school page URL or None.
        """
        soup = BeautifulSoup(page_content, "html.parser")
        main = soup.find("main", id="main") or soup
        articles = main.find_all("article") if main else []
        if not articles:
            self.log.info("No search results (no <article> elements)")
            return None

        for article in articles:
            state_in_article = self._extract_state_from_article(article)
            result_url, result_title = self._extract_title_and_url_from_article(article)
            if not result_url or not result_title:
                continue
            if "educounty.net" not in result_url:
                continue

            if self._is_same_school_via_flash(school, result_title, state_in_article):
                self.log.info(f"Matched school page (Flash): {result_title} -> {result_url}")
                return result_url

        self.log.info("No article matched (Gemini Flash returned false for all)")
        return None

    def _is_same_school_via_flash(
        self,
        school: School,
        result_title: str,
        state_in_article: Optional[str],
    ) -> bool:
        """
        Use Gemini 2.5 Flash to decide if this search result is the same school.
        Returns True only if the model says the result matches the school (handles messy names).
        """
        prompt = get_match_school_result_prompt(
            school,
            result_title or "",
            state_in_article or "",
        )
        try:
            response = self._flash_client.generate_with_gemini(prompt)
            parsed = parse_llm_json_obj(response)
            if parsed and isinstance(parsed, dict):
                return parsed.get("match") is True
        except Exception as e:
            self.log.warning(f"Flash match check failed: {e}")
        return False

    @staticmethod
    def _extract_state_from_article(article) -> Optional[str]:
        """Get state from article's category links (e.g. .../states/delaware/ or link text)."""
        def has_cat_links(c):
            if not c:
                return False
            if isinstance(c, list):
                return "cat-links" in c
            return "cat-links" in str(c)
        cat_span = article.find("span", class_=has_cat_links)
        if not cat_span:
            return None
        for a in cat_span.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if "/states/" in href:
                # e.g. .../states/delaware/ -> "delaware"
                return href.rstrip("/").split("/")[-1].lower()
            text = (a.get_text(strip=True) or "").lower()
            if text and text not in ("school calendars", "states"):
                return text
        return None

    @staticmethod
    def _extract_title_and_url_from_article(article) -> tuple:
        """Get (url, title) from h2.entry-title a. Returns ('', '') if not found."""
        def has_entry_title(c):
            if not c:
                return False
            if isinstance(c, list):
                return "entry-title" in c
            return "entry-title" in str(c)
        h2 = article.find("h2", class_=has_entry_title)
        if not h2:
            return ("", "")
        link = h2.find("a", href=True)
        if not link:
            return ("", "")
        url = (link.get("href") or "").strip()
        title = (link.get_text(strip=True) or "")
        return (url, title)

    def _get_holidays(self, school: School, url: str) -> List[Holiday]:
        """
        Scrape school page as HTML. If div#calendarTable with Date/Event table exists, parse it
        into Holiday objects. Otherwise fall back to LLM (get_analyze_site_content_prompt).
        """
        # Direct document URLs (PDF/image) skip HTML scrape
        if str(url).split(".")[-1].strip().lower() in ["jpeg", "jpg", "png", "pdf", "docx"]:
            raw_holidays = self.generate_json_with_visual_gemini(url, school)
            return self._generate_holiday_obj(raw_holidays, url)

        self.log.info(f"Extracting holidays from: {url}")

        if not self.wss_endpoint:
            self.log.error("BROWSER_WSS environment variable not set")
            return []

        # Scrape as raw HTML so we can parse #calendarTable if present
        html_content = scrape_html_from_wss(url, self.wss_endpoint, return_md=False)
        if not html_content:
            self.log.info(f"Couldn't scrape {url}")
            return []

        # Try parsing the calendar table first (same structure as EduCounty school pages)
        holidays = self._parse_holidays_from_calendar_table(html_content, url)
        if holidays:
            self.log.info(f"Parsed {len(holidays)} holidays from calendar table")
            return holidays

        # Fallback: use LLM to analyze page content (convert same HTML to markdown for prompt)
        page_content = html_to_md_markdownify(html_content)
        if not page_content:
            return []

        prompt = get_analyze_site_content_prompt(school, url, page_content)
        gemini_response = self.generate_with_gemini(prompt)
        parsed_respo = parse_llm_json_obj(gemini_response)

        if parsed_respo is None or (
            not parsed_respo.get("holidays", []) and parsed_respo.get("document_url") is None
        ):
            return []

        raw_holidays = (
            parsed_respo.get("holidays")
            if isinstance(parsed_respo.get("holidays"), list)
            else []
        )
        document_url = (
            parsed_respo.get("document_url")
            if isinstance(parsed_respo.get("document_url"), str)
            else None
        )

        if not raw_holidays and document_url and document_url.strip():
            self.log.info(f"Finding holidays through document: {document_url}")
            ext = str(document_url).split(".")[-1].strip().lower()
            if ext in ["jpeg", "jpg", "png", "pdf", "docx"]:
                raw_holidays = self.generate_json_with_visual_gemini(document_url, school)

        return self._generate_holiday_obj(raw_holidays, url)

    def _parse_holidays_from_calendar_table(self, html_content: str, source_url: str) -> List[Holiday]:
        """
        Parse div#calendarTable table: rows are Date (td) and Event (td). Build Holiday list.
        Structure: <div id="calendarTable"><table><tbody><tr><th>Date</th><th>Event</th></tr><tr><td>...</td><td>...</td></tr>...
        """
        soup = BeautifulSoup(html_content, "html.parser")
        calendar_div = soup.find("div", id="calendarTable")
        if not calendar_div:
            return []

        table = calendar_div.find("table")
        if not table:
            return []

        tbody = table.find("tbody") or table
        rows = tbody.find_all("tr")
        if not rows:
            return []

        # Skip header row (has th)
        data_rows = []
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) >= 2:
                data_rows.append((cells[0], cells[1]))

        holidays: List[Holiday] = []
        academic_year = self._infer_academic_year_from_date_cells([r[0].get_text(strip=True) for r in data_rows])

        for date_cell, event_cell in data_rows:
            date_str = (date_cell.get_text(strip=True) or "").strip()
            event_str = (event_cell.get_text(strip=True) or "").strip()
            event_str = html.unescape(event_str)
            if not date_str or not event_str:
                continue

            # Normalize date range into start/end when possible (e.g. "July 2-4, 2025" -> start "July 2, 2025", end "July 4, 2025")
            date_start, date_end = self._parse_date_range(date_str)

            category = self._infer_category_from_event_name(event_str)

            holidays.append(
                Holiday(
                    academic_year=academic_year,
                    holiday_name=event_str,
                    category=category,
                    date_start=date_start,
                    date_end=date_end,
                    notes=None,
                    source_url=source_url,
                )
            )

        return holidays

    @staticmethod
    def _parse_date_range(date_str: str) -> tuple:
        """
        Return (date_start, date_end). If single date, both same. If range like "July 2-4, 2025"
        or "July 29-August 1, 2025", split into start/end; else return (date_str, date_str).
        """
        date_str = date_str.strip()
        if not date_str:
            return ("", "")

        # Pattern: "Month D-D, YYYY" or "Month D-Month D, YYYY"
        match = re.match(r"^(.+?)\s*[-–—]\s*(.+)$", date_str)
        if not match:
            return (date_str, date_str)

        left, right = match.group(1).strip(), match.group(2).strip()
        year_suffix = ""
        if "," in right:
            year_suffix = ", " + right.split(",")[-1].strip()
            right = right.split(",")[0].strip()

        # "July 2-4, 2025" -> left="July 2", right="4", year_suffix=", 2025" -> start "July 2, 2025", end "July 4, 2025"
        if re.match(r"^\d{1,2}$", right) and left:
            month = left.split()[0] if left.split() else ""
            date_start = left + year_suffix
            date_end = f"{month} {right}{year_suffix}" if month else date_str
            return (date_start, date_end)
        # "July 29-August 1, 2025" -> left="July 29", right="August 1", year_suffix=", 2025"
        if year_suffix:
            return (left + year_suffix, right + year_suffix)
        return (date_str, date_str)

    @staticmethod
    def _infer_academic_year_from_date_cells(date_strings: List[str]) -> str:
        """Infer academic year e.g. 2025-2026 from date strings containing years."""
        years = set()
        for s in date_strings:
            for m in re.finditer(r"\b(20\d{2})\b", s):
                years.add(m.group(1))
        if len(years) >= 2:
            sorted_years = sorted(years)
            return f"{sorted_years[0]}-{sorted_years[1]}"
        if years:
            y = list(years)[0]
            return f"{y}-{str(int(y)+1)}"
        return ""

    @staticmethod
    def _infer_category_from_event_name(event_name: str) -> str:
        """Infer category from event name (Break, Public Holiday, Inset/PD Day, etc.)."""
        name_lower = event_name.lower()
        if "break" in name_lower or "holidays" in name_lower:
            return "Break"
        if "holiday" in name_lower and "staff" not in name_lower:
            return "Public/Federal Holiday"
        if "staff development" in name_lower or "no students" in name_lower or "orientation" in name_lower:
            return "Inset/PD Day"
        if "first day" in name_lower or "students return" in name_lower or "last day" in name_lower:
            return "Term/Half-Term"
        return "Other"

    def _generate_holiday_obj(
        self, raw_holidays: List[dict], source: str | None
    ) -> List[Holiday]:
        """Same as discover_with_serp: build Holiday instances with source_url = source."""
        out: List[Holiday] = []
        for item in raw_holidays:
            if not isinstance(item, dict):
                continue
            try:
                src = source if source is not None else item.get("source_url", "")
                out.append(
                    Holiday(
                        academic_year=(item.get("academic_year") or "").strip(),
                        holiday_name=(item.get("holiday_name") or "").strip(),
                        category=(item.get("category") or "").strip(),
                        date_start=(item.get("date_start") or "").strip(),
                        date_end=(item.get("date_end") or "").strip(),
                        notes=(item.get("notes") or None),
                        source_url=(src.strip() or None),
                    )
                )
            except Exception as e:
                self.log.error(f"Parsing raw holiday: {item}")
                self.log.error(str(e))
                continue
        return out
