"""
Merge multiple output CSV files (from scrape-holidays) into one and remove duplicates.

Duplicates are removed by (source_url, academic_year, holiday_name, date_start, date_end).
First occurrence is kept.

Usage: run from main via `python run.py merge-output-csvs [file1.csv file2.csv ...]`
If no files given, merges all output*.csv in app/sitemap_parser/.
"""

import csv
from pathlib import Path


def run_merge_output_csvs(
    input_paths: list[Path] | None = None,
    output_path: Path | None = None,
) -> Path:
    """
    Read one or more output CSVs (same schema as scrape_holidays output.csv),
    merge and deduplicate by (source_url, academic_year, holiday_name, date_start, date_end),
    write to a single CSV.

    Args:
        input_paths: Paths to CSV files. If None, uses all output*.csv in module dir.
        output_path: Where to write merged CSV. Default: app/sitemap_parser/output_merged.csv

    Returns:
        Path to the merged file.
    """
    base_dir = Path(__file__).resolve().parent
    if input_paths is None:
        input_paths = sorted(base_dir.glob("output*.csv"))
    if not input_paths:
        print("No output CSV files found.")
        return base_dir / "output_merged.csv"

    if output_path is None:
        output_path = base_dir / "output_merged.csv"

    header = [
        "country", "state_name", "region_city", "lea_name", "website", "status",
        "academic_year", "holiday_name", "category", "date_start", "date_end",
        "notes", "source_url",
    ]
    seen: set[tuple[str, ...]] = set()
    rows: list[list[str]] = []

    for path in input_paths:
        if not path.exists():
            print(f"  Skip (not found): {path}")
            continue
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            first = next(reader, None)
            if not first:
                continue
            # Skip header row if present
            if first[0].lower() == "country":
                data_rows = list(reader)
            else:
                data_rows = [first] + list(reader)
            for row in data_rows:
                if len(row) < 13:
                    continue
                key = (row[12], row[6], row[7], row[9], row[10])  # source_url, academic_year, holiday_name, date_start, date_end
                if key not in seen:
                    seen.add(key)
                    rows.append(row)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    print(f"Merged {len(input_paths)} file(s), {len(rows)} unique rows. Output: {output_path}")
    return output_path


if __name__ == "__main__":
    import sys
    paths = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else None
    paths = [
        Path("/Users/gentrithoxhaj/Desktop/SchoolWebsiteHolidaysScraper/app/sitemap_parser/output.csv"),
        Path("/Users/gentrithoxhaj/Desktop/SchoolWebsiteHolidaysScraper/app/sitemap_parser/output-2706---.csv"),
        Path("/Users/gentrithoxhaj/Desktop/SchoolWebsiteHolidaysScraper/app/sitemap_parser/output__1-27006.csv")
    ]
    run_merge_output_csvs(input_paths=paths)
