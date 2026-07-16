from .base import BASE_ROLE

EXTRACTION_PROMPT = f"""
{BASE_ROLE}

Your job is to preserve knowledge, not write notes.

Extract EVERYTHING that would help another AI teach this material.

Capture:

• Core concepts
• Precise definitions
• Step-by-step mechanisms
• Algorithms and procedures
• Why ideas work
• Why they matter
• Intuition or mental models explicitly present in the source
• Examples
• Important technical details
• Common misconceptions mentioned
• Prerequisite knowledge
• Relationships between concepts
• Mathematical formulas
• Warnings or pitfalls

Finally, assess coverage: how much did the source actually say about this topic's concepts?
- "thin": Source barely mentioned it; most extraction fields will be sparse.
- "adequate": Source covered the basics; most fields have meaningful content.  
- "rich": Source went deep with explanations, examples, and nuance.

Capture:

{{
    "concepts": [],
    "definitions": [],
    "mechanisms": [],
    "algorithms": [],
    "reasoning": [],
    "intuition": [],
    "why_it_matters": [],
    "examples": [],
    "important_details": [],
    "common_misconceptions": [],
    "prerequisites": [],
    "connections": [],
    "formulas": [],
    "pitfalls": [],
    "summary": "",
    "coverage": "adequate"
}}

Do NOT teach.

Do NOT summarize into prose.

Do NOT organize as Markdown.

Return ONLY valid JSON matching the schema.
"""