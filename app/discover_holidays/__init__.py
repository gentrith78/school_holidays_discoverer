from app.data_struc import School, Holiday
from app.discover_holidays.search_with_perplexity import HolidayDiscovererPerplexity
from app.discover_holidays.search_with_sitemaps import SearchWithSitemaps

# todo remove dotenv from here once tests are done
import os
from dotenv import load_dotenv
load_dotenv()
####

ppx_api_key = os.getenv("PERPLEXITY_KEY")
perplexity_discoverer = HolidayDiscovererPerplexity(api_key=ppx_api_key)
sitemaps_discoverer = SearchWithSitemaps()

def discover_holidays(school: School) -> School:
    # todo discover holidays: first use perplexity and if that fails use scraping with gemini...

    holidays = sitemaps_discoverer.discover(school)
    if len(holidays) > 0:
        school.holidays = holidays
        return school

    holidays = perplexity_discoverer.discover(school)
    school.holidays = holidays

    if not holidays:
        school.status = "Couldn't find Holiday Data"

    return school
