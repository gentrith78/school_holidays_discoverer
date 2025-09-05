from app.ai_tools.gemini_client import GeminiClient

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


class AnalyzeWebpage(GeminiClient):
    def __init__(self):
        GeminiClient.__init__(self)

        pass