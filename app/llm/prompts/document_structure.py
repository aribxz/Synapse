DOCUMENT_STRUCTURE_PROMPT = """You are adding structural elements to a completed study guide.

You will receive the full document. Your task is to generate TWO things only:

1. A master glossary to append at the very end. Use this format:
   ## 📖 Glossary
   | Term | Definition |
   |------|------------|
   | **term** | one-line definition |
   
   Only include terms that appear in the document. 5-15 terms.

2. A source attribution line: *Sources: ...*

Output format:
---GLOSSARY---
(Glossary markdown here)
---SOURCES---
(Sources line here)

Do NOT modify or rewrite any of the document body. Only output the glossary and sources sections.
"""
