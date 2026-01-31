from app.data_struc import School, Holiday
from app.discover_holidays.discover_with_serp import DiscoverWithSERP
from app.discover_holidays.discover_with_openai import DiscoverWithOpenai
from app.discover_holidays.discover_with_sitemaps import SearchWithSitemaps
from app.discover_holidays.discover_with_perplexity import HolidayDiscovererPerplexity
from app.discover_holidays.discover_with_educounty import DiscoverWithEduCounty

perplexity_discoverer = HolidayDiscovererPerplexity()
sitemaps_discoverer = SearchWithSitemaps()
openai_discoverer = DiscoverWithOpenai()
serp_discoverer = DiscoverWithSERP()
educounty_discoverer = DiscoverWithEduCounty()

def discover_holidays(school: School) -> School:
    """
    Discover holidays using multiple strategies, prioritizing EduCounty.net
    """
    holidays = []
    
    # Strategy 1: Try EduCounty.net first (new primary method)
    holidays = educounty_discoverer.discover(school)
    if holidays and len(holidays) > 0:
        school.holidays = holidays
        school.status = "Found With EduCounty"
        return school
    
    # Strategy 2: Fallback to SERP search
    holidays = serp_discoverer.discover(school)
    if holidays and len(holidays) > 0:
        school.holidays = holidays
        school.status = "Found With SERP Search"
        return school
    
    # Strategy 3: Fallback to OpenAI web search
    holidays = openai_discoverer.discover(school)
    if holidays and len(holidays) > 0:
        school.holidays = holidays
        school.status = "Found With Openai"
        return school
    
    # Strategy 4: Try sitemaps (currently commented out)
    # holidays = sitemaps_discoverer.discover(school)
    # if holidays and len(holidays) > 0:
    #     school.holidays = holidays
    #     school.status = "Found With Sitemaps"
    #     return school
    
    # Strategy 5: Try Perplexity (currently commented out)
    # holidays = perplexity_discoverer.discover(school)
    # if holidays and len(holidays) > 0:
    #     school.holidays = holidays
    #     school.status = "Found With Perplexity"
    #     return school

    # No holidays found
    if not holidays:
        school.holidays = []
        school.status = "Couldn't find Holiday Data"

    return school
