from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Holiday:
    academic_year: str                 # e.g. "2025-2026"
    holiday_name: str                  # e.g. "Spring Break"
    category: str                      # Term/Half-Term, Break, Public Holiday, Inset/PD Day, Other
    date_start: str                    # keep as str, normalize later
    date_end: str
    notes: Optional[str] = None
    source_url: Optional[str] = None

@dataclass
class School:
    country: str
    state_name: str
    region_city: str
    lea_name: str
    website: Optional[str] = None
    holidays: List[Holiday] = None     # list of holiday entries for this school
    status: str = ""
