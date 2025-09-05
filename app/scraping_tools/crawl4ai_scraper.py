import os
import asyncio

from crawl4ai import BrowserConfig, CrawlerRunConfig, AsyncWebCrawler


async def _crawl4ai_scrape(url: str) -> str:
    browser_config = BrowserConfig(
        enable_stealth=True,  # Simple flag to enable
        # headless=False,
        proxy=f'http://{os.getenv("PROXY_USERNAME")}:{os.getenv("PROXY_PASSWORD")}@{os.getenv("PROXY_HOST")}:{os.getenv("PROXY_PORT")}'
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