"""
Merge URLs from sitemap and uncategorized CSV files into a single file.

Usage: run from main via `python run.py merge-urls`
Optional args: sitemap_csv_path, uncategorized_csv_path, output_path
"""

import csv
from pathlib import Path


def _find_latest_csv(directory: Path, pattern: str) -> Path | None:
    """Find the most recent CSV matching the glob pattern in directory."""
    matches = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def run_merge_urls(
    sitemap_csv: Path | None = None,
    uncategorized_csv: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """
    Read URLs from both CSV files, deduplicate, and write to a single merged CSV.

    Args:
        sitemap_csv: Path to educounty_sitemap_urls_*.csv. If None, uses latest in module dir.
        uncategorized_csv: Path to uncategorized_urls_*.csv. If None, uses latest in module dir.
        output_path: Output path. Default: app/sitemap_parser/merged_urls.csv

    Returns:
        Path to the merged output file.
    """
    output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if sitemap_csv is None:
        sitemap_csv = _find_latest_csv(output_dir, "educounty_sitemap_urls_*.csv")
    if uncategorized_csv is None:
        uncategorized_csv = _find_latest_csv(output_dir, "uncategorized_urls_*.csv")

    if not sitemap_csv or not sitemap_csv.exists():
        print("Warning: No sitemap CSV found. Run sitemap-parser first.")
    if not uncategorized_csv or not uncategorized_csv.exists():
        print("Warning: No uncategorized CSV found. Run uncategorized-parser first.")
    if (not sitemap_csv or not sitemap_csv.exists()) and (not uncategorized_csv or not uncategorized_csv.exists()):
        raise FileNotFoundError("No input CSV files found. Run sitemap-parser and uncategorized-parser first.")

    if output_path is None:
        output_path = output_dir / "merged_urls.csv"

    seen: set[str] = set()
    rows: list[tuple[str, str, str]] = []  # (url, source_type, source_detail)

    def add_from_csv(path: Path | None, source_type: str, detail_col: int = 1) -> int:
        count = 0
        if not path or not path.exists():
            return 0
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header and len(header) > 0 and header[0].lower() == "url":
                pass  # skip header row
            else:
                # no header or first row is data - process it
                if header and len(header) > 0:
                    url = header[0].strip()
                    if url.startswith("http") and url not in seen:
                        seen.add(url)
                        detail = header[detail_col] if len(header) > detail_col else ""
                        rows.append((url, source_type, detail))
                        count += 1
            for row in reader:
                if len(row) == 0:
                    continue
                url = row[0].strip()
                if not url or not url.startswith("http") or url in seen:
                    continue
                seen.add(url)
                detail = row[detail_col] if len(row) > detail_col else ""
                rows.append((url, source_type, detail))
                count += 1
        return count

    n_sitemap = add_from_csv(sitemap_csv, "sitemap", detail_col=2)  # url, lastmod, source_sitemap
    n_uncategorized = add_from_csv(uncategorized_csv, "uncategorized", detail_col=1)  # url, source_page

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "source_type", "source_detail"])
        writer.writerows(rows)

    print(f"Merged {len(rows)} unique URLs ({n_sitemap} from sitemap, {n_uncategorized} from uncategorized)")
    print(f"Output: {output_path}")
    return output_path


if __name__ == "__main__":
    run_merge_urls()
