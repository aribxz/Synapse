from .base import BASE_ROLE

MERGE_PROMPT = f"""
{BASE_ROLE}

You are editing a completed technical study guide.

Several independently written sections have already been generated.

Your task is to combine them into one coherent document.

OBJECTIVES

- Preserve all important information.
- Remove duplicated explanations.
- Improve transitions between sections.
- Maintain a consistent heading hierarchy.
- Keep terminology consistent.
- Preserve technical accuracy.
- Do not shorten the document unless removing repetition.
- Do not invent new information.

OUTPUT

Return one polished Obsidian Markdown document.
"""