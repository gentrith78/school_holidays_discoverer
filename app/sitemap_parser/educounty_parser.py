"""
EduCounty Sitemap Parser

Standalone module that extracts all nested URLs from EduCounty post-sitemaps (1-30)
and appends them to a CSV file.

Usage: run from main via `python run.py sitemap-parser`
"""

import csv
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

import requests

# EduCounty post-sitemap URLs 1-30
EDUCOUNTY_SITEMAP_URLS = [
    f"https://www.educounty.net/post-sitemap{i}.xml"
    for i in range(1, 31)
]


def _parse_sitemap_xml(content: str, source_url: str) -> List[Tuple[str, str]]:
    """
    Parse sitemap XML and extract (url, lastmod) pairs.
    Returns list of (loc_url, lastmod_str) tuples.
    Handles both namespaced and non-namespaced sitemap XML.
    """
    results: List[Tuple[str, str]] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML from {source_url}: {e}") from e

    def local_name(elem) -> str:
        return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

    for elem in root.iter():
        if local_name(elem) != "url":
            continue
        loc = ""
        lastmod = ""
        for child in elem:
            tag = local_name(child)
            if tag == "loc" and child.text:
                loc = child.text.strip()
            elif tag == "lastmod" and child.text:
                lastmod = child.text.strip()
        if loc:
            results.append((loc, lastmod))

    return results


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


def _fetch_sitemap(url: str, timeout: int = 15) -> str:
    """Fetch sitemap content via HTTP (uses proxies if configured in env)."""
    proxies = _get_proxies()
    response = requests.get(url, timeout=timeout, proxies=proxies)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def run_educounty_sitemap_parser(
    output_path: Path | None = None,
    append: bool = True,
) -> Path:
    """
    Iterate through EduCounty post-sitemaps 1-30, extract all nested URLs,
    and write to CSV.

    Args:
        output_path: Path to output CSV. Default: app/sitemap_parser/educounty_sitemap_urls_{timestamp}.csv
        append: If True, append to existing file. If False, overwrite.

    Returns:
        Path to the output CSV file.
    """
    output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = output_dir / f"educounty_sitemap_urls_{timestamp}.csv"

    mode = "a" if append and output_path.exists() else "w"
    write_header = mode == "w"

    total_urls = 0
    print(f"EduCounty Sitemap Parser: processing {len(EDUCOUNTY_SITEMAP_URLS)} sitemaps")

    with open(output_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["url", "lastmod", "source_sitemap"])

        for sitemap_url in EDUCOUNTY_SITEMAP_URLS:
            try:
                time.sleep(3)
                content = _fetch_sitemap(sitemap_url)
                pairs = _parse_sitemap_xml(content, sitemap_url)
                for url, lastmod in pairs:
                    writer.writerow([url, lastmod, sitemap_url])
                    total_urls += 1
                print(f"  {sitemap_url}: {len(pairs)} URLs extracted")
            except requests.RequestException as e:
                print(f"  {sitemap_url}: request failed - {e}")
            except ValueError as e:
                print(f"  {sitemap_url}: parse error - {e}")

    print(f"Done. Total URLs written: {total_urls}. Output: {output_path}")
    return output_path

if __name__ == '__main__':
    a = Path("sitemaps.csv")
    run_educounty_sitemap_parser(output_path=a)