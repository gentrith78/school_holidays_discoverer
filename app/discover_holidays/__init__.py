from app.data_struc import School, Holiday
from app.discover_holidays.search import HolidayDiscovererPerplexity

# todo remove dotenv from here once tests are doen
import os
from dotenv import load_dotenv
load_dotenv()
####

ppx_api_key = os.getenv("PERPLEXITY_KEY")
discoverer = HolidayDiscovererPerplexity(api_key=ppx_api_key)


def discover_holidays(school: School) -> School:
    # todo discover holidays: first use perplexity and if that fails use scraping with gemini...
    holidays = discoverer.discover(school)
    return school
