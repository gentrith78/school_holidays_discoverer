"""
EduCounty Uncategorized Parser

Scrapes the uncategorized section (pages 1-21) and extracts article hrefs
from h2.entry-title elements.

Usage: run from main via `python run.py uncategorized-parser`
"""

import csv
import os
import time
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

UNCATEGORIZED_BASE = "https://www.educounty.net/uncategorized/page"
MAX_PAGE = 21


def _get_proxies() -> dict | None:
    """Return proxies dict from env (PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD) or None."""
    host = os.getenv("PROXY_HOST")
    port = os.getenv("PROXY_PORT")
    user = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    if not all([host, port, user, password]):
        return None
    proxy_url = f"http://{user}:{password}@{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}


def _fetch_page(url: str, timeout: int = 15) -> str:
    """Fetch page content via HTTP (uses proxies if configured in env)."""
    proxies = _get_proxies()
    response = requests.get(url, timeout=timeout, proxies=proxies)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _extract_entry_links(html: str) -> list[str]:
    """
    Parse HTML and extract href from h2.entry-title > a elements.
    Example: <h2 class="entry-title ast-blog-single-element" ...><a href="...">...</a></h2>
    """
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for h2 in soup.find_all("h2", class_="entry-title"):
        a = h2.find("a", href=True)
        if a and a.get("href"):
            links.append(a["href"].strip())
    return links


def run_uncategorized_parser(
    output_path: Path | None = None,
    append: bool = True,
) -> Path:
    """
    Iterate through uncategorized pages 1-21, extract hrefs from entry-title links,
    and write to CSV.

    Args:
        output_path: Path to output CSV. Default: app/sitemap_parser/uncategorized_urls_{timestamp}.csv
        append: If True, append to existing file. If False, overwrite.

    Returns:
        Path to the output CSV file.
    """
    output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = output_dir / f"uncategorized_urls_{timestamp}.csv"

    mode = "a" if append and output_path.exists() else "w"
    write_header = mode == "w"

    total_urls = 0
    print(f"EduCounty Uncategorized Parser: processing pages 1 to {MAX_PAGE}")

    with open(output_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["url", "source_page"])

        for page_num in range(1, MAX_PAGE + 1):
            page_url = f"{UNCATEGORIZED_BASE}/{page_num}/"
            try:
                time.sleep(2)
                content = _fetch_page(page_url)
                links = _extract_entry_links(content)
                for href in links:
                    writer.writerow([href, page_url])
                    total_urls += 1
                print(f"  {page_url}: {len(links)} URLs extracted")
            except requests.RequestException as e:
                print(f"  {page_url}: request failed - {e}")
            except Exception as e:
                print(f"  {page_url}: error - {e}")

    print(f"Done. Total URLs written: {total_urls}. Output: {output_path}")
    return output_path


if __name__ == "__main__":
    run_uncategorized_parser()
