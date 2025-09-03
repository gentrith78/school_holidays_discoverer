import os

from app.data_struc import School
from app.discover_website.search import WebsiteDiscovererLLM
from app.ai_tools.gemini_client import GeminiClient


serp_api_key = os.getenv("BRIGHTDATA_SERP_KEY")
gemini_api_key = os.getenv("GEMINI_KEY")

llm_client = GeminiClient()
website_discoverer = WebsiteDiscovererLLM(llm_client=llm_client, serp_api_key=serp_api_key)

def discover_website(school: School) -> School:
    res = website_discoverer.discover(school)

    school.website = res

    return school