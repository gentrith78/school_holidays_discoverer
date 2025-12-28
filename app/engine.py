import os
import json
import traceback
from typing import List
from datetime import datetime
from dataclasses import asdict

from app.data_struc import School
from app.discover_website import discover_website
from app.discover_holidays import discover_holidays
from app.website_health import WebsiteHealthChecker
from app.convert_to_excel import export_school_holidays_to_excel
from app.utils import read_input_csv_USA, configure_logging, ensure_output_dir, read_input_csv_UK

def entrypoint():
    logger = configure_logging()

    logger.info("Starting")
    logger.info("Reading Input")

    # website health checker
    w_h = WebsiteHealthChecker()

    # read input schools
    input_schools: List[School] = read_input_csv_USA()
    if not input_schools:
        logger.error("Could not find any input data")
        raise Exception("No Input data Found")
    else:
        logger.info(f"Total Schools: {len(input_schools)}")

    # process each school
    for school in input_schools:
        try:
            logger.info(f"Processing {school}")

            # check website health #1
            logger.info(f"Checking website health for: {school.website}")
            if not w_h.is_usable(school.website):
                school.status = "Website Health: Broken"
                school.website = ""
            else:
                school.status = "website_ok"

            # discover websites
            if school.website is None or school.website.isspace() or school.website=="":
                logger.info("Website not present or broken, trying to find website")
                school = discover_website(school)
                if school.website is None or school.website.isspace() or school.website == "":
                    logger.info(f"Website NOT Found: {school.website}")
                    school.status = f"Website NOT Found: {school.website}"
                    continue

                logger.info(f"Website Found: {school.website}")

            # check website health #2
            if not "website_ok" in school.status:
                logger.info(f"Checking website health for: {school.website}")
                if not w_h.is_usable(school.website):
                    school.status = "Website Health (check 2): Broken"
                    continue

            # discover holidays
            logger.info(f"Discovering Holidays for {school}")
            school = discover_holidays(school)
            logger.info(f"Total Holidays Found: {len(school.holidays)}")

        except Exception as e:
            logger.error(f"Error Processing: {school}")
            logger.error(traceback.format_exc())
            school.status = str(e)

    # write to output
    logger.info("Writing to Output")
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_fp = ensure_output_dir().joinpath(f"{timestamp}.csv")
        logger.info(f"Writting output to: {output_fp}")
        export_school_holidays_to_excel(input_schools, output_fp)
        # data = [asdict(s) for s in input_schools]
        # with open(f"{output_fp.__str__()}.json", "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass
    logger.info("Process Completed")

if __name__ == '__main__':
    entrypoint()