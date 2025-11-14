from app.data_struc import School, Holiday
from app.discover_holidays.discover_with_serp import DiscoverWithSERP
from app.discover_holidays.discover_with_openai import DiscoverWithOpenai
from app.discover_holidays.discover_with_sitemaps import SearchWithSitemaps
from app.discover_holidays.discover_with_perplexity import HolidayDiscovererPerplexity


perplexity_discoverer = HolidayDiscovererPerplexity()
sitemaps_discoverer = SearchWithSitemaps()
openai_discoverer = DiscoverWithOpenai()
serp_discoverer = DiscoverWithSERP()

def discover_holidays(school: School) -> School:

    # holidays = sitemaps_discoverer.discover(school)
    # if len(holidays) > 0:
    #     school.holidays = holidays
    #     return school
    holidays = serp_discoverer.discover(school)
    school.holidays = holidays
    school.status = "Found With SERP Search"

    if not holidays:
        holidays = openai_discoverer.discover(school)
        school.holidays = holidays
        school.status = "Found With Openai"

    # if not holidays:
    #     holidays = perplexity_discoverer.discover(school)
    #     school.holidays = holidays

    if not holidays:
        school.status = "Couldn't find Holiday Data"

    return school
