import os
import asyncio
from dotenv import load_dotenv

from crawl4ai import BrowserConfig, CrawlerRunConfig, AsyncWebCrawler, ProxyConfig


async def _crawl4ai_scrape(url: str) -> str:
    proxies = ProxyConfig(
        server=f"{os.getenv("PROXY_HOST")}:{os.getenv("PROXY_PORT")}",
        username=os.getenv("PROXY_USERNAME"),
        password=os.getenv("PROXY_PASSWORD")
    )
    browser_config = BrowserConfig(
        enable_stealth=True,  # Simple flag to enable
        proxy_config=proxies,
        headless=True
    )
    run_cfg = CrawlerRunConfig(
        excluded_tags=["nav", "footer"],
        wait_until="networkidle",
        scan_full_page=True
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url, config=run_cfg)
        return result.markdown

def scrape(url: str) -> str:
    return asyncio.run(_crawl4ai_scrape(url))

if __name__ == '__main__':
    load_dotenv()
    u = "https://www.educounty.net/anniston-city-schools-al-calendar-25-26-revised-pdf/"
    print(scrape(u))