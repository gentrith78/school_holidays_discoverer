import sys
from pathlib import Path

from app.engine import entrypoint
from dotenv import load_dotenv

load_dotenv()


def run_sitemap_parser():
    """Run the standalone EduCounty sitemap parser (extracts URLs from post-sitemaps 1-30)."""
    from app.sitemap_parser import run_educounty_sitemap_parser

    run_educounty_sitemap_parser()


def run_uncategorized_parser():
    """Run the EduCounty uncategorized scraper (extracts URLs from uncategorized pages 1-21)."""
    from app.sitemap_parser import run_uncategorized_parser as _run

    _run()


def run_merge_urls():
    """Merge URLs from sitemap and uncategorized CSV files into one."""
    from app.sitemap_parser import run_merge_urls as _run

    _run()


def run_scrape_holidays():
    """Scrape holidays from merged URLs, write to output.csv."""
    from app.sitemap_parser import run_scrape_holidays as _run

    _run()


def run_merge_output_csvs():
    """Merge multiple output CSVs and remove duplicates."""
    from app.sitemap_parser import run_merge_output_csvs as _run

    paths = [Path(p) for p in sys.argv[2:]] if len(sys.argv) > 2 else None
    _run(input_paths=paths)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "sitemap-parser":
        run_sitemap_parser()
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "uncategorized-parser":
        run_uncategorized_parser()
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "merge-urls":
        run_merge_urls()
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "scrape-holidays":
        run_scrape_holidays()
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "merge-output-csvs":
        run_merge_output_csvs()
    else:
        entrypoint()

"""
https://login.xero.com/identity/connect/authorize?response_type=code&client_id=83F7838F841841978F1F2BFDD2E4DEC5&redirect_uri=https://buildpartner.com/&scope=openid profile offline_access email accounting.transactions&state=123&code_challenge=XXXXXXXXX&code_challenge_method=S256
"""