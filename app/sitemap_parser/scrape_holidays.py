"""
EduCounty Holiday Scraper Pipeline

Processes merged_urls.csv one URL at a time: pop first, scrape holidays,
write to output.csv, persist after each URL for fault tolerance.

Usage: run from main via `python run.py scrape-holidays`
"""

import csv
import html as html_module
import os
import re
import time
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

from app.data_struc import Holiday

# US state abbreviation -> full name
ABBR_TO_STATE: dict[str, str] = {
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas",
    "ca": "California", "co": "Colorado", "ct": "Connecticut",
    "de": "Delaware", "dc": "District of Columbia", "fl": "Florida",
    "ga": "Georgia", "hi": "Hawaii", "id": "Idaho", "il": "Illinois",
    "in": "Indiana", "ia": "Iowa", "ks": "Kansas", "ky": "Kentucky",
    "la": "Louisiana", "me": "Maine", "md": "Maryland", "ma": "Massachusetts",
    "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi", "mo": "Missouri",
    "mt": "Montana", "ne": "Nebraska", "nv": "Nevada", "nh": "New Hampshire",
    "nj": "New Jersey", "nm": "New Mexico", "ny": "New York",
    "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio",
    "ok": "Oklahoma", "or": "Oregon", "pa": "Pennsylvania",
    "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota",
    "tn": "Tennessee", "tx": "Texas", "ut": "Utah", "vt": "Vermont",
    "va": "Virginia", "wa": "Washington", "wv": "West Virginia",
    "wi": "Wisconsin", "wy": "Wyoming",
}

OUTPUT_HEADER = [
    "country", "state_name", "region_city", "lea_name", "website", "status",
    "academic_year", "holiday_name", "category", "date_start", "date_end",
    "notes", "source_url",
]

PROCESSED_SCHOOLS_HEADER = [
    "lea_name", "state", "country", "region", "total_holidays_found", "url",
]


def _get_proxies() -> dict | None:
    """Return proxies dict from env or None."""
    host = os.getenv("PROXY_HOST")
    port = os.getenv("PROXY_PORT")
    user = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    if not all([host, port, user, password]):
        return None
    proxy_url = f"http://{user}:{password}@{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}


def _fetch_with_requests(url: str, timeout: int = 30) -> str | None:
    """Fetch page via requests + proxies."""
    try:
        proxies = _get_proxies()
        r = requests.get(url, timeout=timeout, proxies=proxies)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except Exception:
        return None


def _fetch_with_wss(url: str) -> str | None:
    """Fallback: fetch via browser WSS."""
    wss = os.getenv("BROWSER_WSS")
    if not wss:
        return None
    try:
        from app.scraping_tools.brightdata_browser_scraper import scrape_html_from_wss
        return scrape_html_from_wss(url, wss, return_md=False)
    except Exception:
        return None


def _fetch_page(url: str) -> str | None:
    """Fetch page: requests first, WSS fallback."""
    html = _fetch_with_requests(url)
    if html and len(html) > 500:
        return html
    print("  requests failed or short response, trying WSS...")
    return _fetch_with_wss(url)


def _metadata_from_url(url: str) -> tuple[str, str]:
    """Parse URL slug for lea_name and state. Return (lea_name, state_name)."""
    try:
        path = url.rstrip("/").split("/")[-1]
        slug = path.replace(".pdf", "").replace(".html", "").lower()
    except Exception:
        return ("", "")

    # Find state abbrev: common pattern -xxx-YY-YY or -xxx-calendar
    state_name = ""
    for abbr, full in ABBR_TO_STATE.items():
        if f"-{abbr}-" in slug or slug.endswith(f"-{abbr}"):
            state_name = full
            slug = re.sub(rf"-{abbr}(-[a-z0-9-]*)?$", "", slug)
            break

    # Remove year patterns: -25-26, -26-27, -2025, -2026, -revised, -calendar, -pdf
    slug = re.sub(r"-\d{2}-\d{2}(-revised)?(-pdf)?$", "", slug)
    slug = re.sub(r"-\d{4}(-\d{4})?(-revised)?(-pdf)?$", "", slug)
    slug = re.sub(r"-(revised|calendar|pdf)$", "", slug)

    # Humanize: hyphens to spaces, title case
    lea = " ".join(w.capitalize() for w in slug.replace("-", " ").split() if w)
    return (lea, state_name)


def _metadata_from_html(html: str, url: str) -> tuple[str, str, str]:
    """Parse HTML for lea_name, state_name, region_city. Return (lea_name, state_name, region_city)."""
    soup = BeautifulSoup(html, "html.parser")
    lea_name = ""
    state_name = ""
    region_city = ""

    # Links with /states/ in href
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").lower()
        if "/states/" in href:
            state_slug = href.rstrip("/").split("/")[-1]
            state_name = ABBR_TO_STATE.get(state_slug, state_slug.replace("-", " ").title())

    # h1 or .entry-title for page title
    for sel in ["h1", "h2.entry-title", ".entry-title"]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(strip=True)
            if text and len(text) > 3:
                # Strip [PDF], year suffixes
                text = re.sub(r"\s*\[.*?\]\s*", " ", text)
                text = re.sub(r"\s*\d{2}-\d{2}\s*$", "", text)
                text = re.sub(r"\s*\d{4}-\d{4}\s*$", "", text)
                lea_name = text.strip()
                break

    # Fallback to URL
    if not lea_name or not state_name:
        url_lea, url_state = _metadata_from_url(url)
        if not lea_name:
            lea_name = url_lea
        if not state_name:
            state_name = url_state

    return (lea_name or "", state_name or "", region_city or "")


def _pop_first_url(csv_path: Path) -> tuple[str, str, str] | None:
    """Read CSV, return first (url, source_type, source_detail), overwrite file with remaining."""
    if not csv_path.exists():
        return None
    all_rows: list[list[str]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            all_rows.append(row)

    out_rows = []
    first: tuple[str, str, str] | None = None
    for r in all_rows:
        if r[0].lower() == "url":
            out_rows.append(r)
        elif first is None and len(r) >= 1 and r[0].strip().startswith("http"):
            first = (r[0].strip(), r[1] if len(r) > 1 else "", r[2] if len(r) > 2 else "")
        else:
            out_rows.append(r)

    if first is None:
        return None

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(out_rows)
    return first


def _parse_date_range(date_str: str) -> tuple[str, str]:
    """Return (date_start, date_end)."""
    date_str = date_str.strip()
    if not date_str:
        return ("", "")
    match = re.match(r"^(.+?)\s*[-–—]\s*(.+)$", date_str)
    if not match:
        return (date_str, date_str)
    left, right = match.group(1).strip(), match.group(2).strip()
    year_suffix = ""
    if "," in right:
        year_suffix = ", " + right.split(",")[-1].strip()
        right = right.split(",")[0].strip()
    if re.match(r"^\d{1,2}$", right) and left:
        month = left.split()[0] if left.split() else ""
        return (left + year_suffix, f"{month} {right}{year_suffix}" if month else date_str)
    if year_suffix:
        return (left + year_suffix, right + year_suffix)
    return (date_str, date_str)


def _infer_academic_year(date_strings: List[str]) -> str:
    """Infer academic year e.g. 2025-2026."""
    years = set()
    for s in date_strings:
        for m in re.finditer(r"\b(20\d{2})\b", s):
            years.add(m.group(1))
    if len(years) >= 2:
        return f"{sorted(years)[0]}-{sorted(years)[1]}"
    if years:
        y = list(years)[0]
        return f"{y}-{str(int(y)+1)}"
    return ""


def _infer_category(event_name: str) -> str:
    """Infer category from event name."""
    n = event_name.lower()
    if "break" in n or "holidays" in n:
        return "Break"
    if "holiday" in n and "staff" not in n:
        return "Public/Federal Holiday"
    if "staff development" in n or "no students" in n or "orientation" in n:
        return "Inset/PD Day"
    if "first day" in n or "students return" in n or "last day" in n:
        return "Term/Half-Term"
    return "Other"


def _parse_holidays_from_calendar_table(html_content: str, source_url: str) -> List[Holiday]:
    """Parse div#calendarTable table into Holiday list."""
    soup = BeautifulSoup(html_content, "html.parser")
    calendar_div = soup.find("div", id="calendarTable")
    if not calendar_div:
        return []
    table = calendar_div.find("table")
    if not table:
        return []
    tbody = table.find("tbody") or table
    rows = tbody.find_all("tr")
    data_rows = [(c[0], c[1]) for tr in rows if (c := tr.find_all("td")) and len(c) >= 2]
    if not data_rows:
        return []

    academic_year = _infer_academic_year([r[0].get_text(strip=True) for r in data_rows])
    holidays: List[Holiday] = []
    for date_cell, event_cell in data_rows:
        date_str = (date_cell.get_text(strip=True) or "").strip()
        event_str = (event_cell.get_text(strip=True) or "").strip()
        event_str = html_module.unescape(event_str)
        if not date_str or not event_str:
            continue
        date_start, date_end = _parse_date_range(date_str)
        holidays.append(
            Holiday(
                academic_year=academic_year,
                holiday_name=event_str,
                category=_infer_category(event_str),
                date_start=date_start,
                date_end=date_end,
                notes=None,
                source_url=source_url,
            )
        )
    return holidays


def run_scrape_holidays(
    merged_path: Path | None = None,
    output_path: Path | None = None,
    processed_schools_path: Path | None = None,
) -> None:
    """
    Process merged_urls.csv: pop first URL, scrape, write to output.csv and processed_schools.csv, repeat.
    Removes URL from queue only after success. On scrape failure, URL stays in queue.
    """
    base_dir = Path(__file__).resolve().parent
    base_dir.mkdir(parents=True, exist_ok=True)

    merged_path = merged_path or base_dir / "merged_urls.csv"
    output_path = output_path or base_dir / "output.csv"
    processed_schools_path = processed_schools_path or base_dir / "processed_schools.csv"

    if not merged_path.exists():
        print("No merged_urls.csv found. Run merge-urls first.")
        return

    processed = 0
    while True:
        row = _pop_first_url(merged_path)
        if row is None:
            break
        url, _src_type, _src_detail = row
        print(f"Processing: {url}")

        # Direct document URLs: skip (would need WSS/Gemini visual)
        path_lower = url.lower().split("?")[0].rstrip("/")
        if path_lower.endswith((".pdf", ".docx", ".jpg", ".jpeg", ".png")):
            print("  Skipping direct document URL (would need WSS/Gemini)")
            continue

        html = _fetch_page(url)
        if not html:
            print("  Fetch failed, re-adding URL to front of queue")
            with open(merged_path, "r", newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            with open(merged_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                for i, r in enumerate(rows):
                    if r and r[0].lower() == "url":
                        w.writerow(r)
                        w.writerow([url, _src_type, _src_detail])
                        w.writerows(rows[i + 1 :])
                        break
                else:
                    w.writerow(["url", "source_type", "source_detail"])
                    w.writerow([url, _src_type, _src_detail])
                    w.writerows(rows)
            break

        lea_name, state_name, region_city = _metadata_from_html(html, url)
        country = "USA"
        website = url
        status = ""

        holidays = _parse_holidays_from_calendar_table(html, url)

        write_header = not output_path.exists()
        with open(output_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(OUTPUT_HEADER)
            if holidays:
                for h in holidays:
                    w.writerow([
                        country, state_name, region_city, lea_name, website, status,
                        h.academic_year, h.holiday_name, h.category, h.date_start, h.date_end,
                        h.notes or "", h.source_url or "",
                    ])
            else:
                w.writerow([
                    country, state_name, region_city, lea_name, website, status,
                    "", "", "", "", "", "", "",
                ])
        # Append to processed_schools.csv
        ps_write_header = not processed_schools_path.exists()
        with open(processed_schools_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if ps_write_header:
                w.writerow(PROCESSED_SCHOOLS_HEADER)
            w.writerow([lea_name, state_name, country, region_city, len(holidays), url])

        processed += 1
        print(f"  Wrote {len(holidays)} holidays ({lea_name or 'unknown'})")
        time.sleep(2)

    print(f"Done. Processed {processed} URLs. Output: {output_path}, Schools: {processed_schools_path}")


if __name__ == "__main__":
    run_scrape_holidays()
