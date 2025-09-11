import os
import json

import urllib.parse
from typing import Dict, List

import requests

def serp_search(query: str, max_results = 5) -> List[Dict]:
    bright_data_endpoints = "https://api.brightdata.com/request"

    out: List[dict] = []
    headers = {"Authorization": f"Bearer {os.getenv('BRIGHTDATA_SERP_KEY')}",
               "Content-Type": "application/json"
               }

    query = urllib.parse.quote_plus(query)

    payload = {
        "zone": "serp_api_lir",
        "url": f"https://www.google.com/search?q={query}&brd_json=1",
        "format": "json"
    }

    try:
        resp = requests.post(bright_data_endpoints, headers=headers, json=payload)
        resp.raise_for_status()
        serialised_resp = json.loads(resp.json()['body'])
    except Exception as e:
        print(f"SERP error: {e}")
        return []

    for el in serialised_resp.get("organic", ""):
        out.append(
            {
                "link": el.get("link", ""),
                "title": el.get("title", ""),
                "description": el.get("description"),
            }
        )

    return out[:max_results]