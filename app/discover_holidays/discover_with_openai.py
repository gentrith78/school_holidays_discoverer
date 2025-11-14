import os
import json
import logging
from typing import List


from app.scraping_tools import scrape
from app.data_struc import School, Holiday
from app.ai_tools import get_perplexity_get_holidays_prompt, GeminiVisualClient, OpenAiWebSearchClient, GeminiClient, get_analyze_site_content_prompt
from app.utils import parse_llm_json_obj

class DiscoverWithOpenai(OpenAiWebSearchClient, GeminiVisualClient, GeminiClient):
    def __init__(self):
        OpenAiWebSearchClient.__init__(self)
        GeminiVisualClient.__init__(self)
        GeminiClient.__init__(self)

        self.log = logging.getLogger("main_logger")

    def discover(self, school: School):
        self.log.info("Discovering holidays through openai")
        prompt = get_perplexity_get_holidays_prompt(school)

        raw = self.generate_with_open_ai_web_search(prompt)

        if not raw:
            return []

        obj = parse_llm_json_obj(raw) if raw else None

        holidays_out: List[Holiday] = []

        if not obj.get('holidays', []) and obj.get('document_url', None) is None:
            return holidays_out

        if obj and isinstance(obj, dict):
            document_url = (obj.get("document_url") or None) if isinstance(obj.get("document_url"), str) else None
            raw_holidays = obj.get("holidays") if isinstance(obj.get("holidays"), list) else []

            if not raw_holidays and not document_url.isspace() and not document_url == "" and document_url is not None:
                self.log.info(f"Finding Holidays through document: {document_url}")
                if str(document_url).split(".")[-1].strip() in ["jpeg", "jpg", "png", "pdf"]:
                    raw_holidays = self.generate_json_with_visual_gemini(document_url, school)
                else:
                    self.log.info("Document url not a pdf or image")
                    raw_holidays = self.extract_with_page_analyze(school, document_url)


            for item in raw_holidays:
                if not isinstance(item, dict):
                    continue
                try:
                    if document_url is not None:
                        source = document_url
                    else:
                        source = item.get("source_url", "")

                    holidays_out.append(Holiday(
                        academic_year=(item.get("academic_year") or "").strip(),
                        holiday_name=(item.get("holiday_name") or "").strip(),
                        category=(item.get("category") or "").strip(),
                        date_start=(item.get("date_start") or "").strip(),
                        date_end=(item.get("date_end") or "").strip(),
                        notes=(item.get("notes") or None),
                        source_url=(source.strip() or None),
                    ))
                except Exception:
                    continue


        return holidays_out

    def extract_with_page_analyze(self, school: School, url: str) -> List[dict]:
        """
        perplexity returned a document url that is not an image or pdf so we are trying to scrape it and extract data
        - sometimes this page returns a pdf document url so we have to download and extract only holidays from it
        :returns only a list of holidays as dict or empty list, never a document url
        """
        self.log.info(f"Extracting Holidays by analyzing page content: {url}")
        page_content = scrape(url)

        if page_content is None:
            self.log.info(f"Couldn't scrape {url}")
            return []

        prompt = get_analyze_site_content_prompt(school, url, page_content)
        gemini_response = self.generate_with_gemini(prompt)

        parsed_respo = parse_llm_json_obj(gemini_response)


        if not parsed_respo.get('holidays', []) and parsed_respo.get('document_url', None) is None:
            return []

        raw_holidays = parsed_respo.get("holidays") if isinstance(parsed_respo.get("holidays"), list) else []
        document_url = (parsed_respo.get("document_url") or None)\
            if isinstance(parsed_respo.get("document_url"), str) else None

        if not raw_holidays and not document_url.isspace() and not document_url == "" and document_url is not None:
            self.log.info(f"Finding Holidays through document (in page analysis func): {document_url}")
            if str(document_url).split(".")[-1].strip() in ["jpeg", "jpg", "png", "pdf"]:
                raw_holidays = self.generate_json_with_visual_gemini(document_url, school)

        return raw_holidays


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv("")