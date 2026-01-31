"""
Holiday Validator Module

Validates that required holidays are present in a school's holiday list.
Updates the school status to "reliably found" if all required holidays are present,
or "missing dates" if any are missing.
"""

import logging
import re
from typing import List, Set
from app.data_struc import School, Holiday

# Required holiday names that must be present
REQUIRED_HOLIDAYS = [
    "Labor Day",
    "Thanksgiving",
    "Winter Break",
    "Martin Luther King Jr",
    "Presidents Day",
    "Spring Break",
    "Memorial Day",
]

logger = logging.getLogger("main_logger")


def _normalize_holiday_name(name: str) -> str:
    """
    Normalize a holiday name for comparison:
    - Convert to lowercase
    - Remove extra whitespace
    - Remove common punctuation
    - Remove common suffixes like "Day", "Holiday", "Break"
    """
    if not name:
        return ""
    
    # Convert to lowercase and strip
    normalized = name.lower().strip()
    
    # Remove common punctuation
    normalized = re.sub(r"[.,'\-]", "", normalized)
    
    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    
    return normalized


def _get_holiday_keywords(required_name: str) -> List[str]:
    """
    Generate keywords and variations for a required holiday name.
    Returns a list of normalized keywords that should match the holiday.
    """
    normalized = _normalize_holiday_name(required_name)
    keywords = [normalized]
    
    # For compound names, also add individual words
    words = normalized.split()
    if len(words) > 1:
        # Add key words (skip common words like "day", "break")
        key_words = [w for w in words if w not in ["day", "break", "holiday", "holidays"]]
        keywords.extend(key_words)
    
    return keywords


def _matches_required_holiday(holiday_name: str, required_name: str) -> bool:
    """
    Check if a holiday name matches a required holiday name.
    Handles case-insensitive matching and common variations.
    """
    if not holiday_name or not required_name:
        return False
    
    normalized_holiday = _normalize_holiday_name(holiday_name)
    normalized_required = _normalize_holiday_name(required_name)
    
    # Direct match after normalization
    if normalized_required in normalized_holiday or normalized_holiday in normalized_required:
        return True
    
    # Special handling for specific holidays with common variations
    required_lower = required_name.lower()
    holiday_lower = holiday_name.lower()
    
    # Martin Luther King Jr variations
    if "martin luther king" in required_lower:
        mlk_terms = ["martin luther king", "mlk", "martin luther king jr", "martin luther king jr day"]
        if any(term in normalized_holiday for term in mlk_terms):
            return True
    
    # Presidents Day variations (handles President's Day, Presidents' Day, etc.)
    if "presidents" in required_lower and "day" in required_lower:
        president_terms = ["presidents day", "president day", "presidents", "presidents day", "washington"]
        if any(term in normalized_holiday for term in president_terms):
            # Make sure it's not "Vice Presidents Day" or similar
            if "president" in normalized_holiday:
                return True
    
    # Winter Break variations
    if "winter" in required_lower and "break" in required_lower:
        winter_terms = ["winter break", "winter holiday", "winter holidays", "winter recess", "winter vacation"]
        if any(term in normalized_holiday for term in winter_terms):
            return True
    
    # Spring Break variations
    if "spring" in required_lower and "break" in required_lower:
        spring_terms = ["spring break", "spring holiday", "spring holidays", "spring recess", "spring vacation"]
        if any(term in normalized_holiday for term in spring_terms):
            return True
    
    # Thanksgiving variations
    if "thanksgiving" in required_lower:
        if "thanksgiving" in normalized_holiday:
            return True
    
    # Labor Day variations (handles both US "Labor" and UK "Labour")
    if "labor" in required_lower or "labour" in required_lower:
        labor_terms = ["labor day", "labour day"]
        if any(term in normalized_holiday for term in labor_terms):
            return True
    
    # Memorial Day variations
    if "memorial" in required_lower and "day" in required_lower:
        if "memorial" in normalized_holiday and "day" in normalized_holiday:
            return True
    
    return False


def validate_required_holidays(school: School) -> School:
    """
    Validate that all required holidays are present in the school's holiday list.
    Updates school.status to:
    - "reliably found" if all required holidays are present
    - "missing dates" if any required holidays are missing
    
    Only validates if the school has holidays. If holidays were successfully discovered
    (status indicates success), the status will be replaced with validation result.
    Error statuses are preserved.
    
    Args:
        school: School object with holidays list
        
    Returns:
        School object with updated status
    """
    # Only validate if we have holidays
    if not school.holidays or len(school.holidays) == 0:
        logger.debug(f"No holidays to validate for {school.lea_name}")
        return school
    
    # Don't overwrite error statuses - preserve them
    error_indicators = ["broken", "not found", "error", "couldn't find", "exception"]
    if any(indicator in school.status.lower() for indicator in error_indicators):
        logger.debug(f"Skipping validation due to error status: {school.status}")
        return school
    
    # Track which required holidays were found
    found_holidays: Set[str] = set()
    holiday_names = [h.holiday_name for h in school.holidays if h.holiday_name]
    
    # Check each required holiday
    for required_holiday in REQUIRED_HOLIDAYS:
        for holiday_name in holiday_names:
            if _matches_required_holiday(holiday_name, required_holiday):
                found_holidays.add(required_holiday)
                logger.debug(f"Found required holiday '{required_holiday}' as '{holiday_name}' for {school.lea_name}")
                break
    
    # Update status based on findings
    missing_holidays = set(REQUIRED_HOLIDAYS) - found_holidays
    
    if len(missing_holidays) == 0:
        school.status += "--reliably found"
        logger.info(f"All required holidays found for {school.lea_name} - Status: reliably found")
    else:
        school.status += "--missing dates"
        logger.warning(f"Missing required holidays for {school.lea_name}: {', '.join(missing_holidays)} - Status: missing dates")
    
    return school

