# 📓 Day 1 — Setting Up the Factory

**Date:** July 5, 2026  
**Phase:** Part 1 — Ingestion Engine (just started)

---

## What's the big picture?

You're building a **knowledge pipeline**. Think of it like a factory assembly line:

1. **Raw materials come in** — YouTube videos, PDFs, Word docs, PowerPoints, webpages.
2. **Each material gets processed** — text is pulled out of each one.
3. **An AI brain reads it all** — Groq (the LLM) turns it into proper, structured notes.
4. **Clean product comes out** — beautiful Markdown notes ready for Obsidian.

Today you only built **Step 1 and Step 2** — the "intake" part of the factory. Nothing talks to Groq yet, no notes come out yet. You're just making sure you can accept different file types and rip the text out of them.

---

## How the code is organised

Here's the folder structure and what each part does:

```
run.py              ← The "on" switch. Starts the whole app.
config.py           ← Settings (like secret passwords, API keys).
app/
├── __init__.py     ← Builds the Flask app (the "factory builder").
├── routes/         ← Where the website URLs are defined.
├── controllers/    ← Will decide what to do with user input (empty for now).
├── models/         ← The "blueprints" — what a piece of knowledge looks like.
├── ingestion/      ← The extraction machines (pulls text from files).
├── services/       ← The "manager" that runs the whole extraction process.
└── templates/      ← The HTML pages the user sees.
```

---

## The flow — what happens when something gets processed

Think of it like a post office sorting system:

```
📬 A file/URL arrives
      ↓
🏷️  It gets wrapped in a KnowledgeSource (an envelope with labels)
      ↓
📮 The Router looks at the label ("Oh, this is a PDF")
      ↓
📋 The Registry finds the right Extractor ("Use the PDF machine!")
      ↓
⚙️  The Extractor rips the text out
      ↓
📨 The envelope now has raw_content inside it
```

---

## Key concepts you learned today

### 1. The App Factory Pattern (`app/__init__.py`)

Instead of creating the Flask app globally, you have a function called `create_app()` that **builds and returns** the app. This is a best practice — it means you can create multiple versions of the app (for testing, for production, etc.) without them stepping on each other.

### 2. Data Models — What a "piece of knowledge" looks like

You created two model classes in `app/models/`:

- **`KnowledgeSource`** — One single piece of input. Like one PDF, or one YouTube video. It's a `dataclass` (Python's shortcut for creating classes that mainly hold data). Each source has:
  - `source_type` — what kind of input it is (PDF, YouTube, etc.)
  - `title` — a display name
  - `raw_content` — starts empty, gets filled with extracted text
  - `metadata` — extra info (like a file path, or a video ID)
  - `status` — tracks where it is in the pipeline (pending → extracting → extracted → failed)
  - `id` — a unique ID so you can tell sources apart

- **`KnowledgeCollection`** — A group of sources bundled together (not coded yet, file is empty).

### 3. Enums — Fixed lists of options (`app/models/enums.py`)

You used Python's `Enum` class to define **fixed sets of valid values**. Think of it like a dropdown menu — you can only pick from the options listed.

- `SourceType` — the types of input: YOUTUBE, WEBPAGE, PDF, DOCX, PPTX, TXT
- `ProcessingStatus` — the stages: PENDING → EXTRACTING → EXTRACTED → ... → COMPLETED / FAILED

### 4. The Extractor System — Polymorphism in action

This is the most architecturally interesting part. You built a **plugin-like system** for extractors:

- **`BaseExtractor`** — An abstract class (a "contract"). It says: *"Any extractor MUST have an `extract()` method."* It uses `ABC` (Abstract Base Class) to enforce this.

- **5 concrete extractors** — Each one knows how to handle a specific file type:
  - `PDFExtractor` — uses `PyMuPDF (fitz)` to read PDF pages
  - `DocxExtractor` — uses `python-docx` to read Word paragraphs
  - `PPTXExtractor` — uses `python-pptx` to loop through slides and shapes
  - `YouTubeExtractor` — uses `youtube-transcript-api` to grab video transcripts
  - `WebExtractor` — uses `trafilatura` to download and extract clean text from URLs

- **`ExtractorRegistry`** — A dictionary that maps each `SourceType` to its extractor. Like a phone book: "Need a PDF extracted? Here's the PDFExtractor."

- **`InputRouter`** — Gets a source, asks the registry for the right extractor, and calls it. It doesn't care *which* extractor — it just says "you handle it." This is **polymorphism** — the router treats all extractors the same way, even though they do completely different things internally.

### 5. The Extraction Service (`app/services/extraction_service.py`)

This is the **manager**. It takes a whole collection of sources, loops through each one, and:
1. Marks it as "extracting"
2. Sends it to the router
3. Saves the extracted text back
4. Marks it as "extracted" (or "failed" if something went wrong)

The `try/except` block catches errors so that if one file fails, the rest still get processed.

### 6. Routes and Templates

Super simple for now:
- One route (`/`) that shows a basic HTML page with just a heading.
- The template is a barebones `index.html`.

---

## What's NOT done yet

- `input_controller.py` — empty file, not coded yet
- `knowledge_collection.py` — empty file, not coded yet
- No frontend form to upload files
- No connection to Groq/LLM
- No Markdown output yet
- The `.env` has placeholder API keys (you'll need to put your real Groq key in)

---

## Quick reference — OOP concepts used

| Concept | Where | What it does |
|---|---|---|
| **Dataclass** | `KnowledgeSource` | Auto-generates `__init__`, keeps code clean for data containers |
| **Enum** | `SourceType`, `ProcessingStatus` | Restricts values to a fixed set of options |
| **Abstract class (ABC)** | `BaseExtractor` | Forces all extractors to implement `extract()` |
| **Inheritance** | Each extractor extends `BaseExtractor` | Reuses the "contract" while providing specific behaviour |
| **Polymorphism** | `InputRouter.route()` | Calls `.extract()` on whatever extractor it gets, doesn't care which one |
| **Factory pattern** | `create_app()` | Builds and returns the Flask app on demand |
| **Registry pattern** | `ExtractorRegistry` | Maps types to handlers, so the router doesn't need `if/elif` chains |

---

## 💬 My honest review

**The approach of using ChatGPT as a guide is genuinely smart.** You're not copy-pasting a finished project — you're building it step by step with explanations. The fact that you're leaving comments like *"Don't give me a shared dictionary"* and *"Bridge between OS and computer system"* tells me you're actually engaging with the material and trying to understand it in your own words. That's the right instinct.

**What's going well:**
- The architecture is production-quality for where you're at. Seriously — the BaseExtractor → Registry → Router pattern is a real-world design that professional codebases use. You're not doing beginner spaghetti code.
- You planned before coding. The frozen architecture doc shows you thought about the whole pipeline before jumping in. That discipline matters.
- You're learning **patterns** (factory, registry, polymorphism), not just syntax. That transfers to every future project.

**Where to be careful:**
- Right now, you're at the stage where the architecture "makes sense when explained" but might not feel fully intuitive yet. That's normal. The moment it clicks — probably when you actually run data through the pipeline end-to-end — it'll all fall into place.
- Don't feel bad about the "following instructions" feeling. Building real architecture *should* feel like that at first. It's like learning chess openings — you follow them before you understand them, and then one day you just *get* why the moves are what they are.
- The `KnowledgeCollection` and `input_controller` are empty, which means the system can't actually run end-to-end yet. Next session, wiring those up will make everything feel much more concrete.

**Verdict:** You're doing this the right way. Keep going. 🤝
