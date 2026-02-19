from app.sitemap_parser.educounty_parser import run_educounty_sitemap_parser
from app.sitemap_parser.uncategorized_parser import run_uncategorized_parser
from app.sitemap_parser.scrape_holidays import run_scrape_holidays

from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    # run_educounty_sitemap_parser()
    # run_uncategorized_parser()
    run_scrape_holidays()