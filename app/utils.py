import os
import re
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

from app.data_struc import School

def read_input_csv_USA() -> List[School]:
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

def read_input_csv_UK() -> List[School]:
    schools: List[School] = []

    input_dir_path = Path(os.path.abspath(__file__)).parent.parent.joinpath("input")
    for file in input_dir_path.iterdir():
        if file.__str__().strip().endswith(".csv"):
            with file.open(mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    school = School(
                        country=row.get("Country", "").strip(),
                        state_name=row.get("Region", "").strip(),
                        region_city="",
                        lea_name=row.get("LEA", "").strip(),
                        website=row.get("Holiday URL", "").strip() or None,
                        holidays=[]  # empty for now, to be filled later
                    )
                    schools.append(school)

    return schools

def ensure_output_dir():
    input_dir_path = Path(os.path.abspath(__file__)).parent.parent.joinpath("output")
    if not input_dir_path.exists():
        os.makedirs(input_dir_path, exist_ok=True)
    return input_dir_path

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

def parse_llm_json_obj(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly parse a JSON OBJECT returned by an LLM.
    Expected shape: {"holidays": [...], "document_url": "https://..."}
    Accepts code fences, outer quotes, trailing commas, and truncation after last '}'.

    Returns dict or None.
    """
    if not text:
        return None

    t = text.strip()

    # Strip code fences
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE).strip()

    # Strip single outer quotes (common when printed or embedded)
    if (t.startswith("'") and t.endswith("'")) or (t.startswith('"') and t.endswith('"')):
        t = t[1:-1].strip()

    # First attempt
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Try to find the first '{' block and salvage until last '}'
    m = re.search(r"\{\s*.+", t, flags=re.DOTALL)
    if not m:
        return None

    obj_txt = m.group(0)
    last_brace = obj_txt.rfind("}")
    if last_brace != -1:
        obj_txt = obj_txt[: last_brace + 1]

    # Remove trailing commas like ", }" or ", ]"
    obj_txt = re.sub(r",\s*([}\]])", r"\1", obj_txt)

    try:
        obj = json.loads(obj_txt)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None



if __name__ == '__main__':
    read_input_csv_USA()
