from .base import BASE_ROLE

OUTLINE_PROMPT = f"""
{BASE_ROLE}

You are planning a technical study guide.

Your job is NOT to teach.

Your job is to analyze the educational material and produce a writing plan for another AI.

For every major topic, produce exactly:

1. Title
2. Short Description (1-2 sentences)
3. Role (choose ONE)
   - Motivation
   - Intuition
   - Mechanism
   - Procedure
   - Example
   - Edge Case
   - Takeaway
4. Source Chunks (which chunk numbers this topic belongs to)

Rules:

- This source material spans {{NUM_CHUNKS}} chunks. Based on this length, you MUST produce at least {{MIN_TOPICS}} topics and at most {{MAX_TOPICS}} topics. This is a hard requirement — do not go below {{MIN_TOPICS}}.
- Split distinct concepts into separate topics. Do NOT merge unrelated ideas.
- Preserve the logical flow of the source.
- Do not split a single concept across multiple topics.
- Do not explain concepts in detail.
- Do not write study notes.
- Return only the outline. Use EXACTLY this format for every topic (no markdown, no headings, no bold):

Topic:
    Title: <topic title>
    Description: <1-2 sentence description>
    Role: <Motivation | Intuition | Mechanism | Procedure | Example | Edge Case | Takeaway>
    Source Chunks: <comma-separated chunk numbers>

- Do NOT add markdown headings (###), bullet lists, or bold formatting.
- Do NOT wrap the response in code fences.
- Do NOT use <think> tags or any chain-of-thought reasoning.
- Output only the topics in the format shown above, one after another.
"""