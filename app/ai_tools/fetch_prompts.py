import os
from typing import List
from pathlib import Path

from app.data_struc import School, Holiday


def get_perplexity_get_holidays_prompt(school: School) -> str:
    prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                   .joinpath("perplexity_discover_holidays.txt"))

    with open(prompt_path.__str__(), "r") as f:
        prompt = f.read()

    q_hint = f'{school.lea_name} {school.state_name} {school.country} school holiday dates calendar term dates academic year site:({school.website})' if school.website else f'{school.lea_name} {school.state_name} {school.country} school holiday dates calendar term dates'

    prompt = (prompt.replace("<<school.lea_name>>", school.lea_name)
              .replace("<<school.state_name>>", school.state_name)
              .replace("<<school.country>>", school.country)
              .replace("<<school.website>>", school.website)
              .replace("<<q_hint>>", q_hint)
              )

    return prompt.strip()

def get_analyze_site_content_prompt(school: School, sitemap: str, page_content: str) -> str:
    prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                   .joinpath("gemini_analyze_site_content.txt"))

    with open(prompt_path.__str__(), "r") as f:
        prompt = f.read()

    prompt = (prompt.replace("<<school.lea_name>>", school.lea_name)
              .replace("<<school.state_name>>", school.state_name)
              .replace("<<school.country>>", school.country)
              .replace("<<site_root>>", school.website)
              .replace("<<page_url>>", sitemap)
              .replace("<<page_markdown>>", page_content)
              )

    return prompt

def get_analyze_sitemaps_prompt(school: School, sitemaps: List[str]) -> str:
    prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                   .joinpath("gemini_analyze_sitemaps.txt"))

    with open(prompt_path.__str__(), "r") as f:
        prompt = f.read()

    prompt = (prompt.replace("<<school.lea_name>>", school.lea_name)
     .replace("<<school.state_name>>", school.state_name)
     .replace("<<school.country>>", school.country)
     .replace("<<site_root>>", school.website)
     .replace("<<sitemaps_list>>", str(sitemaps))
     )

    return prompt

def get_gemini_visual_prompt(school: School) -> str:
    prompt_path = (Path(os.path.abspath(__file__)).parent.parent.joinpath("PROMPTS")
                   .joinpath("gemini_extract_dates_from_visual.txt"))

    with open(prompt_path.__str__(), "r") as f:
        prompt = f.read()
        prompt = prompt.replace("<<lea>>", school.lea_name)

    return prompt
