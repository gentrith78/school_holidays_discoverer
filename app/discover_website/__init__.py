from app.data_struc import School
from app.discover_website.search import WebsiteDiscovererLLM
from app.ai_tools.gemini_client import GeminiClient

# todo remove dotenv from here once tests are doen
import os
from dotenv import load_dotenv
load_dotenv()
####


serp_api_key = os.getenv("BRIGHTDATA_SERP_KEY")
gemini_api_key = os.getenv("GEMINI_KEY")

llm_client = GeminiClient
discoverer = WebsiteDiscovererLLM(llm_client=llm_client, serp_api_key=serp_api_key)

def discover_website(school: School) -> School:
    res = discoverer.discover(school)

    if res["website"]:
        # todo ask Josh for zone name and test further this module
        school.website = res["website"]

    return school