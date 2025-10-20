from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from markdownify import markdownify as md

def html_to_md_markdownify(html: str) -> str:
    return md(html, heading_style="ATX")  # simple and reliable

def scrape_html_from_wss(url: str, wss_endpoint: str) -> str:
    """
    Connects to a remote browser via WSS endpoint, opens the URL,
    waits for content to load, scrolls to trigger lazy loads, and
    returns the full HTML content as a string.
    """
    def auto_scroll(page, max_idle_rounds=5, step_px=1200, pause_ms=600, hard_cap_scrolls=200):
        """Scroll until no new content loads."""
        idle_rounds = 0
        scrolls = 0
        prev_height = -1
        while scrolls < hard_cap_scrolls and idle_rounds < max_idle_rounds:
            page.evaluate(f"window.scrollBy(0, {step_px});")
            page.wait_for_timeout(pause_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=1500)
            except PlaywrightTimeoutError:
                pass
            height = page.evaluate("document.body.scrollHeight")
            if height == prev_height:
                idle_rounds += 1
            else:
                idle_rounds = 0
                prev_height = height
            scrolls += 1

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(wss_endpoint)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=120000)
        except PlaywrightTimeoutError:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)

        page.wait_for_timeout(800)
        auto_scroll(page)
        page.wait_for_timeout(500)

        html_content = page.content()

        context.close()
        browser.close()

        return html_to_md_markdownify(html_content)


if __name__ == '__main__':
    from dotenv import load_dotenv
    import os

    load_dotenv()
    wss_ = os.environ.get("BROWSER_WSS")
    u = "https://calendar.asd20.org/district/annual-calendar/2025"
    scrape_html_from_wss(url=u, wss_endpoint=wss_)