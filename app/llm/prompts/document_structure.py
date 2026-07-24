DOCUMENT_STRUCTURE_PROMPT = """You are adding structural elements to a completed study guide.

You will receive the full document. Your task is to generate THREE things:

1. A grouped Table of Contents organized by subject area.

   Read the full document and group related ## headings into parts.
   For example, if the document covers linear regression topics together, then logistic regression topics, group them as:

   ## 🗺️ Navigation

   ### Part I: Linear Regression
   - [[#Ordinary Least Squares]]
   - [[#R-squared and MSE]]
   - [[#Gradient Descent for Linear Regression]]

   ### Part II: Logistic Regression
   - [[#Log Odds and the Logit Function]]
   - [[#Maximum Likelihood Estimation]]
   - [[#McFadden's Pseudo R-squared]]

   Rules:
   - The TOC MUST start with `## 🗺️ Navigation` on the very first line of the TOC section.
   - Use Roman numerals (I, II, III, IV, V, VI) for parts.
   - Include EVERY ## heading from the document — none omitted.
   - The part label must describe the subject area (not the video/source title).
   - Each heading must be a valid [[#Exact Heading]] wiki link matching the document exactly.
   - Headings may start with an emoji character — include it in the link text exactly as it appears.
   - Do NOT add extra entries that don't correspond to actual ## headings.
   - Wrap the TOC between ---TOC--- and ---ENDTOC--- markers.

2. A master glossary to append at the very end. Use this format:
   ## 📖 Glossary
   | Term | Definition |
   |------|------------|
   | **term** | one-line definition |
   
   Only include terms that appear in the document. 5-15 terms.
   Wrap between ---GLOSSARY--- and ---ENDGLOSSARY---.

3. A source attribution line: *Sources: ...*
   Wrap between ---SOURCES--- and ---ENDSOURCES---.

Output format:
---TOC---
...
---ENDTOC---
---GLOSSARY---
...
---ENDGLOSSARY---
---SOURCES---
...
---ENDSOURCES---

Do NOT modify or rewrite any of the document body. Only output the TOC, glossary, and sources sections.
"""