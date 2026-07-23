DOCUMENT_STRUCTURE_PROMPT = """You are adding structural elements to a completed study guide.

You will receive the full document. Your task is to generate TWO things only:

1. A navigation Table of Contents to prepend at the very top. Use this format:
   ## 🗺️ Navigation
   [[#Section One Title]] · [[#Section Two Title]] · [[#Section Three Title]]
   Include ALL major sections (## headings).
   If two headings start with the same emoji, omit the emoji from the second one in the ToC to avoid confusion.

2. A master glossary to append at the very end. Use this format:
   ## 📖 Glossary
   | Term | Definition |
   |------|------------|
   | **term** | one-line definition |
   
   Only include terms that appear in the document. 5-15 terms.

3. A source attribution line: *Sources: ...*

Output format:
---TOC---
(ToC markdown here)
---GLOSSARY---
(Glossary markdown here)
---SOURCES---
(Sources line here)

Do NOT modify or rewrite any of the document body. Only output the TOC, glossary, and sources sections.
"""
