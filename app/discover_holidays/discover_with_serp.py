import logging
from typing import List

from app.utils import parse_llm_json_obj
from app.data_struc import School, Holiday
from app.scraping_tools import serp_search, scrape
from app.ai_tools import GeminiClient, GeminiVisualClient, get_analyze_site_content_prompt

class DiscoverWithSERP(GeminiClient, GeminiVisualClient):
    def __init__(self):
        GeminiClient.__init__(self)
        GeminiVisualClient.__init__(self)
        self.log = logging.getLogger("main_logger")

    def discover(self, school: School) -> List[Holiday]:
        self.log.info("Extracting Holidays using SERP search")
        holidays_out: List[Holiday] = []

        query = self._build_query(school)
        serp_result: List[dict] = serp_search(query, max_results=10)
        best_serp_matches = []
        for s in serp_result:
            if str(s).count(school.lea_name.lower().strip()) < 0:
                continue
            best_serp_matches.append(
                {
                "serp_data":s,
                "counted_lea":str(s).count(school.lea_name.lower().strip())

            }
            )

        sorted_list = sorted(best_serp_matches, key=lambda x: x["counted_lea"], reverse=True)

        if not sorted_list:
            return []

        for s in sorted_list[:3]:
            url = s.get("serp_data", {}).get("link")
            if len(holidays_out) >= 30:
                # there are more than 30 holidays found which means most likely they're found
                continue
            if url:
                try:
                    holidays: List[Holiday] = self._get_holidays(school, url)
                    holidays_out.extend(holidays)
                    # todo optionally add a step to check if this sources was relevant or not... if it's confident then dont continue to the next source (check chatgp)
                except Exception as e:
                    self.log.error(f"Error Analyzing {url}")
                    self.log.error(str(e))
                    continue

        # remove duplicates...
        return self.deduplicate_by_dates(holidays_out)

    def _get_holidays(self, school: School, url):
        # scrape
        if str(url).split(".")[-1].strip() in ["jpeg", "jpg", "png", "pdf", "docx"]:
            raw_holidays = []
            document_url = url
        else:
            self.log.info(f"Extracting Holidays by analyzing page content: {url}")
            page_content = scrape(url)

            if page_content is None:
                self.log.info(f"Couldn't scrape {url}")
                return []

            # analyze
            prompt = get_analyze_site_content_prompt(school, url, page_content)
            gemini_response = self.generate_with_gemini(prompt)

            # get with visual gemini if needed
            parsed_respo = parse_llm_json_obj(gemini_response)

            if (parsed_respo is None or
                    (not parsed_respo.get('holidays', []) and parsed_respo.get('document_url', None) is None)):
                return []

            raw_holidays = parsed_respo.get("holidays") if isinstance(parsed_respo.get("holidays"), list) else []
            document_url = (parsed_respo.get("document_url") or None)\
                if isinstance(parsed_respo.get("document_url"), str) else None

        if not raw_holidays and not document_url.isspace() and not document_url == "" and document_url is not None:
            self.log.info(f"Finding Holidays through document (in page analysis func): {document_url}")
            if str(document_url).split(".")[-1].strip() in ["jpeg", "jpg", "png", "pdf", "docx"]:
                raw_holidays = self.generate_json_with_visual_gemini(document_url, school)

        if document_url is not None:
            source = document_url
        else:
            source = None

        return self._generate_holiday_obj(raw_holidays, source)

    def _generate_holiday_obj(self, raw_holidays: List[dict], source: str or None) -> List[Holiday]:
        out: List[Holiday] = []

        for item in raw_holidays:
            if not isinstance(item, dict):
                continue
            try:
                if source is None:
                    source = item.get("source_url", "")
                out.append(Holiday(
                    academic_year=(item.get("academic_year") or "").strip(),
                    holiday_name=(item.get("holiday_name") or "").strip(),
                    category=(item.get("category") or "").strip(),
                    date_start=(item.get("date_start") or "").strip(),
                    date_end=(item.get("date_end") or "").strip(),
                    notes=(item.get("notes") or None),
                    source_url=(source.strip() or None),
                ))
            except Exception as e:
                self.log.error(f"Parsing raw holiday: {item}")
                self.log.error(str(e))
                continue

        return out

    @staticmethod
    def deduplicate_by_dates(holidays: list[Holiday]) -> list[Holiday]:
        seen = set()
        unique = []
        for h in holidays:
            key = (h.date_start, h.date_end)
            if key not in seen:
                seen.add(key)
                unique.append(h)
        return unique

    @staticmethod
    def _build_query(school: School) -> str:
        # return f"school holidays or term dates for {school.lea_name} school district 2025-2026 -facebook -twitter -instagram -linkedin -pinterest -tiktok"
        return f"site:{school.website.replace("http://www.","").replace("http://", "")} ('term date' OR 'academic calendar' OR 'school calendar')"
