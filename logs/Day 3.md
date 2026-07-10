# 📓 Day 3 — Teaching the AI How to Think

**Date:** July 9, 2026
**Phase:** Part 3 — Intelligence Engine (refining the LLM layer)
**Hours worked:** ~2 hours

---

## What happened today, in one sentence?

Today was a focused, quality-first session — you didn't add many new pieces, but you significantly upgraded the *brain* of the project. The AI now knows what it's supposed to do, how to think before writing, and how to carry context between chunks.

---

## The two big problems you solved

### Problem 1: The AI had no instructions

At the end of Day 2, `SYSTEM_PROMPT` was literally an empty string `""`. The AI was reading your content and guessing what to do with it. The result was raw JSON code blocks instead of actual notes.

Today you replaced that emptiness with real, carefully written instructions.

### Problem 2: Each chunk was processed independently — no memory

On Day 2, when a long document got split into 5 chunks, the AI treated chunk 2 as if it had never seen chunk 1. It would re-introduce concepts, repeat definitions, restart headings from scratch. The notes were disjointed.

Today you fixed this by giving the AI a "memory" of what it already wrote.

---

## What changed — file by file

### 1. The `prompts.py` file is gone, replaced by a whole `prompts/` folder

On Day 2: one file `app/llm/prompts.py` with an empty `SYSTEM_PROMPT = ""`.

On Day 3: that single file has been deleted and replaced with a proper folder `app/llm/prompts/` containing four files:

```
app/llm/prompts/
├── __init__.py       ← Makes the folder importable, exports the two main prompts
├── base.py           ← The shared "personality" of the AI
├── study_notes.py    ← The main prompt for writing notes
└── outline.py        ← A separate prompt for planning the document structure
```

Think of this like upgrading from a Post-it note on the fridge that says "cook dinner" to a full recipe book with separate instructions for each course. The logic is now organised, reusable, and easy to update independently.

---

### 2. `base.py` — the AI's core identity

This is a short, shared piece that defines what the AI fundamentally *is*:

> *"You are an expert educator, technical writer, and instructional designer. Your purpose is to transform educational material into professional study notes. Never produce conversational responses. Return only Markdown."*

Both other prompts (`study_notes.py` and `outline.py`) inherit this identity by including `BASE_ROLE` at the top. It's like the first paragraph of a job description — before you tell someone the specific tasks, you tell them what kind of person they should be on the job.

---

### 3. `study_notes.py` — the main prompt (the most important file today)

This is the biggest change of the day. It's a carefully structured prompt split into clear sections:

| Section | What it tells the AI |
|---|---|
| **MISSION** | The goal: understanding, not summarisation |
| **THINKING PROCESS** | Think first, write second. Identify topics, find relationships, separate essential ideas from filler |
| **WRITING PROCESS** | For every concept: explain *what*, *why*, *how*, and any trade-offs |
| **WRITING STYLE** | Teach naturally. Assume reader is smart but new. Don't just shorten — rewrite for clarity |
| **ORGANIZATION** | Use meaningful section titles, not "Introduction / Overview / Conclusion" |
| **MARKDOWN** | Obsidian-compatible format with specific rules for headings, bullets, tables, code blocks |
| **IMPORTANT** | Never invent information. Never introduce outside knowledge. Preserve math and code |
| **OUTPUT** | Return only Markdown. Start immediately, no preamble |

This prompt is what determines the *quality* of your final notes. A bad prompt produces notes that look like AI wrote them. A good prompt produces notes that feel like a smart person wrote them. This one is good.

---

### 4. `outline.py` — a separate "planning" prompt

This is a second, different type of prompt for a new feature: **generating a document outline** before writing notes.

The idea: before the AI starts writing section by section, it first looks at *all* the content together and plans what the document should cover and in what order. Like a writer drafting a table of contents before writing the chapters.

The prompt is strict: *"You are NOT writing notes. Your only job is to identify the major topics and their logical order."*

This feature is built and the code is wired up, but **it isn't being called in the main pipeline yet** — it's ready and waiting. This is good architectural thinking: build the capability, integrate later when needed.

---

### 5. `prompt_builder.py` — upgraded with memory and context

This file was rewritten to handle two jobs instead of one. The `build()` method (for note generation) now accepts new parameters:

- `chunk_index` — which number chunk this is (e.g. chunk 3 out of 7)
- `total_chunks` — the total number of chunks
- `previous_notes` — the notes already generated from previous chunks

The user prompt it sends to the AI now reads something like:

> *"You are writing section 3 of 7. Here are the notes already generated for sections 1–2: [previous notes]. Continue naturally. Do not repeat what's already been explained."*

This is the fix for the "no memory" problem. The AI can now build on what it already said rather than starting from scratch every time.

A new method `build_outline()` was also added — this is the one that uses `OUTLINE_PROMPT` and sends all the chunks combined to generate the document plan.

---

### 6. `llm/models.py` — two new data structures added

Two new dataclasses were added to represent things needed for the outline feature:

- **`PromptContext`** — stores extra context about the source being processed: what type it is (PDF, YouTube etc.), which chunk we're on, total chunks, and the document title. This will be used to give the AI richer context in future.

- **`OutlineSection`** — represents one topic in the outline: a title and a one-sentence summary. (Note: there's a small typo in the code — `sumamry` instead of `summary` — worth fixing.)

- **`Outline`** — a list of `OutlineSection` objects. The whole planned document structure in one object.

---

### 7. `ai_service.py` — smarter loop + new outline method

The `generate_from_chunks()` method was upgraded to pass context between chunks:

```
Before: each chunk → AI → notes (no memory)
After:  each chunk → AI (with previous notes as context) → notes → passed to next chunk
```

It now tracks `previous_notes` and passes it along at each step. The AI at chunk 3 sees what chunk 1 and 2 produced, so it doesn't repeat itself.

A new method `generate_outline()` was added — it joins all chunks into one big text and sends it to the `build_outline()` prompt to get a document plan back.

---

### 8. YouTube extractor overhauled (`app/ingestion/extractors/youtube_extractor.py`)

The old extractor required you to manually pre-extract the video ID and put it in `metadata["video_id"]`. That was clunky.

The new version is self-sufficient:
- A standalone helper function `extract_video_id_from_url(url)` handles both URL formats:
  - Long format: `youtube.com/watch?v=ABC123` → extracts `ABC123`
  - Short format: `youtu.be/ABC123` → extracts `ABC123`
- Uses Python's built-in `urlparse` to safely slice the URL into parts
- Uses `TextFormatter` from the transcript API for cleaner output
- Replaces all newlines with spaces to keep the transcript as one flowing text

This also fixes the failing unit tests that were written on Day 2 — they referenced `extract_video_id_from_url` which didn't exist yet. Now it does.

---

### 9. `notes_test/` folder — proof the pipeline produced real output

This new folder contains three saved outputs from test runs:

| File | What it is |
|---|---|
| `test1.md` | 758 lines of AI notes from a YouTube video about Large Language Models |
| `test2.md` | Notes generated from your LinkedIn PDF (same test as Day 2 but now in proper Markdown) |
| `test3.md` | Notes about Missing Data in Random Forests (likely from another YouTube video) |

`test1.md` is the most important one to look at. It's 758 lines of real, structured Markdown notes from a real YouTube video. **The pipeline works end to end and produces readable output.** That's the milestone for today.

Compare it to `outputs/notes.md` from Day 2 — that one was a raw JSON code block. Today's output is actual clean Markdown with headings, bullet points, and readable prose. That's entirely because of the new system prompt.

---

## What's NOT done yet

- **The outline feature isn't integrated into the main pipeline** — `generate_outline()` exists in `ai_service.py` but `pipeline_service.py` doesn't call it yet. The plan is probably to call it first, use the outline to guide how chunks are grouped, then generate notes. That's a more advanced two-pass approach.
- **`PromptContext` isn't used yet** — the data structure exists but nothing passes it to the prompt builder yet. It's a placeholder for richer context in future.
- **Typo in `models.py`** — `sumamry` on line 24 should be `summary`. Small but worth fixing before you start using `OutlineSection`.
- **No JSON parsing / `KnowledgeDocument`** — the output is still raw text joined with `---` separators, not parsed into the structured `KnowledgeDocument` model. The notes work but aren't structured data yet.
- **Frontend is still bare HTML** — no styling, no progress indicators, nothing visual.

---

## Concepts reinforced today

| Concept | Where | What it does |
|---|---|---|
| **Prompt engineering** | `study_notes.py`, `outline.py` | Writing precise instructions that shape AI behaviour — an underrated skill |
| **Inheritance via f-strings** | `outline.py`, `study_notes.py` | Both include `{BASE_ROLE}` so the base identity flows into both automatically |
| **Stateful loops** | `ai_service.py` | Tracking `previous_notes` across loop iterations — one variable carries state from one step to the next |
| **URL parsing** | `youtube_extractor.py` | `urlparse` dissects a URL into its component parts (scheme, netloc, path, query) |
| **Package organisation** | `app/llm/prompts/` | Turning a single file into a proper sub-package using `__init__.py` to control what gets exported |

---

## 💬 My opinion on Day 3

**Two hours, focused on quality. That's exactly the right call.**

The temptation after a big Day 2 is to keep adding features. But you didn't do that — you stopped and asked "is what we have actually good?" and the answer was no. The system prompt was empty. The AI had no memory between chunks. The notes looked like a machine wrote them. You fixed all three of those things today.

**`study_notes.py` deserves a special mention.** That's not just a string — it's genuine prompt engineering. The structure of it (think first, then write; explain what/why/how; use meaningful headings; never invent information) shows real understanding of what makes AI output good versus mediocre. Most people learning this stuff just write "summarize this" and wonder why the output is shallow. You've gone a level deeper.

**The `test1.md` output is your best evidence yet that this project is working.** 758 lines of notes on LLMs from a single YouTube video, in clean readable Markdown, with logical sections and real explanations — not a JSON blob, not a summary, actual notes. That's a meaningful result.

**The two things I'd tackle next:**

1. **Fix the typo** (`sumamry` → `summary`) before it causes a confusing bug later.
2. **Integrate the outline** — even a simple version where you call `generate_outline()` first and print/log it for now. Once you see the outline alongside the notes, you'll have ideas for how to use it to improve structure.

**Overall:** Short session, but targeted and effective. The project is producing real, usable output now. You're in the refinement phase of the Intelligence Engine, which means the hard structural work is done and the remaining work is about making the output *better*. That's a good place to be on Day 3. 🔥
