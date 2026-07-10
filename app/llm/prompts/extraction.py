from .base import BASE_ROLE

EXTRACTION_PROMPT = f"""
{BASE_ROLE}

You are extracting knowledge from educational material.

Do NOT teach.

Do NOT summarize.

Do NOT format Markdown.

Extract every important piece of information into the following JSON structure.

{{
    "concepts": [],
    "definitions": [],
    "mechanisms": [],
    "algorithms": [],
    "examples": [],
    "formulas": [],
    "important_details": [],
    "pitfalls": [],
    "connections": []
}}

Rules

- Preserve every important technical fact.
- Never invent information.
- If a field has no content, return an empty list.
- Return ONLY valid JSON.
"""