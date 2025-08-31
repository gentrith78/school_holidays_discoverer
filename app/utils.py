import os
import csv
import logging
from typing import List
from pathlib import Path
from datetime import datetime

from app.data_struc import School

def read_input_csv() -> List[School]:
    schools: List[School] = []

    input_dir_path = Path(os.path.abspath(__file__)).parent.parent.joinpath("input")
    for file in input_dir_path.iterdir():
        if file.__str__().strip().endswith(".csv"):
            with file.open(mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    school = School(
                        country=row.get("COUNTRY", "").strip(),
                        state_name=row.get("STATENAME", "").strip(),
                        region_city=row.get("REGION_CITY", "").strip(),
                        lea_name=row.get("LEA_NAME", "").strip(),
                        website=row.get("WEBSITE", "").strip() or None,
                        holidays=[]  # empty for now, to be filled later
                    )
                    schools.append(school)

    return schools

def configure_logging():
    # Create a logger with the name 'my_project'
    logger = logging.getLogger("main_logger")
    logger.setLevel(logging.DEBUG)  # Set to the lowest level to capture all messages

    # Prevent adding handlers multiple times if setup_logger() is called more than once
    if not logger.handlers:
        # Ensure the 'logs' directory exists
        logs_dir = Path(os.path.abspath(__file__)).parent.parent.joinpath("logs")
        if not logs_dir.exists():
            os.makedirs(logs_dir.__str__())

        # Create a timestamp for the log file name
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_filename = os.path.join(logs_dir, f"log_{timestamp}.log")

        # Create file handler that logs messages to a file
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)

        # Create a stream handler for output to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Create a common formatter and set it for both handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


if __name__ == '__main__':
    read_input_csv()
