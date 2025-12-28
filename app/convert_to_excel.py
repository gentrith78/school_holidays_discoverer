from app.data_struc import *
import logging

logger = logging.getLogger("main_logger")

import pandas as pd
from typing import List

def schools_to_holiday_rows(schools: List[School]) -> list[dict]:
    rows: list[dict] = []

    for school in schools:
        if not school.holidays:
            rows.append({
                "country": school.country,
                "state_name": school.state_name,
                "region_city": school.region_city,
                "lea_name": school.lea_name,
                "website": school.website,
                "status": school.status,

                # Holiday fields left empty
                "academic_year": "",
                "holiday_name": "",
                "category": "",
                "date_start": "",
                "date_end": "",
                "notes": "",
                "source_url": "",
            })
            continue
        for h in school.holidays:
            rows.append({
                # --- School-level fields ---
                "country": school.country,
                "state_name": school.state_name,
                "region_city": school.region_city,
                "lea_name": school.lea_name,
                "website": school.website,
                "status": school.status,

                # --- Holiday-level fields ---
                "academic_year": h.academic_year,
                "holiday_name": h.holiday_name,
                "category": h.category,
                "date_start": h.date_start,
                "date_end": h.date_end,
                "notes": h.notes,
                "source_url": h.source_url,
            })

    return rows


def export_school_holidays_to_excel(schools: List[School], filename: str = "school_holidays.csv"):
    rows = schools_to_holiday_rows(schools)

    if not rows:

        print("No holidays found, nothing to export.")
        logger.warning("No holidays found, nothing to export.")
        return

    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)
    print(f"Exported {len(df)} holiday rows to {filename}")
    logger.info(f"Exported {len(df)} holiday rows to {filename}")