import logging
from typing import List

from app.utils import read_input_csv, configure_logging
from app.data_struc import School
from app.discover_website import discover_website
from app.discover_holidays import discover_holidays


def entrypoint():
    logger = configure_logging()

    logger.info("Starting")
    logger.info("Reading Input")

    # read input schools
    input_schools: List[School] = read_input_csv()
    if not input_schools:
        logger.error("Could not find any input data")
        raise Exception("No Input data Found")
    else:
        logger.info(f"Total Schools: {len(input_schools)}")

    # process each school
    for school in input_schools:
        try:
            logger.info(f"Processing {school}")
            # discover websites
            if school.website is None or school.website.isspace() or school.website=="":
                logger.info("Website not present, trying to find website")
                school = discover_website(school)
                logger.info(f"Website Found: {school.website}")

            # discover holidays
            logger.info(f"Discovering Holidays for {school}")
            school = discover_holidays(school)
            logger.info(f"Total Holidays Found: {len(school.holidays)}")

        except Exception as e:
            logger.error(f"Error Processing: {school}")

    # write to output
    logger.info("Writing to Output")
    # todo write to output...
    logger.info("Process Completed")

if __name__ == '__main__':
    entrypoint()