# 📓 Day 2 — The Pipeline Comes Alive

**Date:** July 8, 2026
**Phase:** Part 1 (Ingestion) → Part 2 (Processing) → Part 3 (LLM) — all scaffolded in one day.
**Hours worked:** ~6 hours

---

## What happened today, in one sentence?

Yesterday you built the skeleton. Today you connected everything and made a real, working, end-to-end pipeline — you can now drop a PDF or URL into the app and it spits out an AI-generated notes file. 🎉

---

## The big change: the full pipeline is now wired up

On Day 1, the factory had departments but no conveyor belt connecting them.  
Today you built the conveyor belt. The journey a file takes now looks like this:

```
You upload a PDF (or paste a YouTube link)
         ↓
Flask receives it at the /process route
         ↓
InputController sorts it into a KnowledgeCollection
         ↓
PipelineService runs it through every stage:
   ① ExtractionService   → rips raw text out of the file
   ② DocumentProcessor   → cleans up the text
   ③ ChunkingService     → cuts it into bite-sized pieces
   ④ AIService           → sends each piece to Groq (the AI)
   ⑤ MarkdownRenderer   → stitches AI outputs together
   ⑥ ExportService       → saves a notes.md file
         ↓
Flask sends you the file as a download
```

The proof it works: there's an actual `outputs/notes.md` file generated from what appears to be a test PDF of your own LinkedIn/portfolio. The AI read it and produced structured JSON notes about you. The pipeline ran. It worked.

---

## What's new — file by file

### 1. `KnowledgeCollection` is finally filled in (`app/models/`)

On Day 1 this file was blank. Now it's a proper dataclass:
- Holds a **list** of `KnowledgeSource` objects (all your PDFs, URLs, etc. grouped together)
- Has a `topic`, a `status`, a `created_at` timestamp, and a unique `id`

Think of it like an **order ticket at a restaurant**. Each item on the order is a `KnowledgeSource`. The whole order sheet is the `KnowledgeCollection`. Previously you had the idea of an order ticket but hadn't printed the template yet — now it's done.

### 2. `KnowledgeDocument` — a new output model (`app/models/knowledge_document.py`)

This is a brand new file. It describes what the **final output** looks like structurally, using three nested classes:

- **`KnowledgeBlock`** — one single unit of content. Like one paragraph, or one bullet list, or one heading.
- **`KnowledgeSection`** — a group of blocks under a title. Like a chapter.
- **`KnowledgeDocument`** — the whole document, made of sections.

Analogy: imagine a textbook. The **textbook** is the `KnowledgeDocument`. Each **chapter** is a `KnowledgeSection`. Each **paragraph or diagram** inside a chapter is a `KnowledgeBlock`.

This model exists to represent the ideal *structure* of the output — but it's not fully used yet in the active pipeline. It's set up for the future when the AI output is properly parsed.

### 3. `BlockType` enum added (`app/models/enums.py`)

You added a third enum alongside `SourceType` and `ProcessingStatus`. `BlockType` defines all the possible types a block of content can be: `HEADING`, `PARAGRAPH`, `BULLETS`, `CODE`, `FORMULA`, `TABLE`, `QUOTE`, etc. This is future-proofing — when the AI returns structured output, you'll use this to categorise each piece.

### 4. `SourceFactory` — a smarter way to create sources (`app/controllers/source_factory.py`)

This is a new class with a very simple job: **look at what the user gave you and figure out what type it is**.

- If someone uploads a `.pdf` file → creates a `KnowledgeSource` with `SourceType.PDF`
- If someone uploads a `.docx` → `SourceType.DOCX`
- If someone pastes a `youtube.com` link → `SourceType.YOUTUBE`
- If someone pastes any other URL → `SourceType.WEBPAGE`

It uses a pattern called a **static method** — meaning you don't need to create a `SourceFactory` object to use it. You just call `SourceFactory.from_upload_file(file)` directly. Think of it like a vending machine — you don't need to build a relationship with it, you just press the button and it gives you what you need.

### 5. `InputController` is now fully coded (`app/controllers/input_controller.py`)

On Day 1 this was an empty file. Now it does the real work of handling an incoming request from the browser:

1. Creates an empty `KnowledgeCollection` (a blank order ticket)
2. Loops through every uploaded file, saves it to the `uploads/` folder, creates a `KnowledgeSource` for it using the `SourceFactory`
3. Loops through every URL pasted in the text box, creates a `KnowledgeSource` for each
4. Passes the whole collection to the `PipelineService` to run through all the stages
5. Returns the final output file path

The controller is the **receptionist**. It doesn't know how to process anything — it just greets you, takes your documents, hands them to the right department, and gives you the receipt at the end.

### 6. `PipelineService` — the master conductor (`app/services/pipeline_service.py`)

This is the most important new file. It's the one that actually connects all the stages together in order. Think of it as the **assembly line manager** who makes sure each station gets the work and passes it to the next.

The stages it runs, in order:
1. `ExtractionService` → text is pulled out
2. `DocumentProcessor` → text is cleaned
3. `ChunkingService` → text is split into chunks
4. `AIService` → AI generates notes from each chunk
5. `MarkdownRenderer` → all AI outputs are joined into one big Markdown string
6. `ExportService` → that string is saved to a `.md` file

### 7. The Processing Engine is built (`app/processing/`)

Three new utility classes that run between extraction and the AI:

- **`TextCleaner`** — removes messy formatting like triple blank lines, random tabs, and Windows-style line endings. Like tidying up a rough draft before handing it to an editor.
- **`MetadataExtractor`** — counts characters and words in each source and stores those numbers in the source's metadata. No processing, just measurement.
- **`TokenEstimator`** — estimates how many "tokens" (the unit AI models charge per) the text contains. The rule of thumb it uses: 1 token ≈ 4 characters.
- **`DocumentProcessor`** — the class that runs all three above on every source in the collection. The manager of the cleaning crew.

### 8. The Chunking Engine is built (`app/chunking/`)

AI models have a limit on how much text they can read in one go — like handing someone a book and asking them to summarise it all in one thought. Not practical. So you cut the text into chunks first.

- **`Chunk`** — a dataclass representing one piece of text. Has an `id`, the `text` itself, and the `estimated_tokens`.
- **`Chunker`** — the actual cutting logic. It walks through the words one by one, fills up a "bucket" of words until it's nearly at the token limit (3000 by default), then seals that bucket as a Chunk and starts a new one.

This is important because it means the AI only ever sees a manageable portion at a time, rather than the entire document all at once.

### 9. The LLM layer is built (`app/llm/`)

This is the brain of the project. Five files:

- **`models.py`** — two simple dataclasses: `LLMRequest` (what you send to the AI: a system prompt + a user prompt) and `LLMResponse` (what you get back: the raw text output).
- **`prompts.py`** — holds `SYSTEM_PROMPT`. Right now it's an empty string — this is a critical placeholder you'll fill in soon. The system prompt is the "personality" instructions you give the AI before it reads your content.
- **`schemas.py`** — a JSON schema that tells the AI *exactly* what structure its output should follow: a document with a title, sections, and blocks. This is like giving a chef a plating diagram — you're telling it not just what to cook but how to arrange it on the plate.
- **`prompt_builder.py`** — assembles the final prompt. It takes the raw chunk text and wraps it in a user message that says: "Here is the content. Output MUST match this JSON schema. Here's the schema."
- **`client.py`** — the actual connection to Groq. Sends the request to the `llama-3.3-70b-versatile` model and returns the response. The way it's structured (system role + user role) is the standard "chat" format that all modern AI APIs use.

### 10. Rendering and Export (`app/rendering/`, `app/services/export_service.py`)

- **`MarkdownRenderer`** — takes a list of AI text outputs and joins them with `---` separators into one long Markdown document.
- **`ExportService`** — saves that Markdown string into `app/outputs/notes.md` and returns the file path so Flask can serve it as a download.

### 11. The route now does something real (`app/routes/main.py`)

The `/process` route now:
1. Takes the browser's uploaded files and URL text
2. Passes them to `InputController.process_request()`
3. Sends back the generated `notes.md` file as a download

There are also debug/test routes added:
- `/test-chunk` — a quick route you wired up to test whether chunking works on a test PDF, returns chunk count and sizes as JSON
- `/test-ai` (commented out) — a leftover from testing the AI connection directly

### 12. The frontend form (`app/templates/index.html`)

No longer just a heading. Now has an actual working form:
- A file upload button (allows multiple files)
- A text area to paste URLs (one per line)
- A "Generate Notes" button that submits to `/process`

It's bare-bones HTML — no styling yet — but it's fully functional for testing the backend.

### 13. Tests written (`tests/`)

Two test files have appeared:

- **`test_routes.py`** — checks that the `/test-clunk` route (note: looks like a typo, probably meant `/test-chunk`) returns something other than a 404. Basic smoke test.
- **`test_youtube_extractor.py`** — tests a new helper function `extract_video_id_from_url()`. Checks that both `youtube.com/watch?v=...` and `youtu.be/...` short URLs return the correct video ID. This means the YouTube extractor was also improved to be more robust.

### 14. New folders at the root

- **`uploads/`** — where uploaded files land temporarily before being processed
- **`outputs/`** — where the final `notes.md` is saved
- **`logs/`** — empty for now, ready for future logging
- **`development log/`** — contains `Log 1.md` and `Log 2.md`, your session notes from ChatGPT

---

## The full pipeline, visualised

```
Browser
   │  (uploads files + pastes URLs)
   ▼
Flask Route (/process)
   │
   ▼
InputController
   │  (saves files, creates KnowledgeSources via SourceFactory)
   ▼
KnowledgeCollection
   │  (a bundle of all your inputs)
   ▼
PipelineService
   ├─① ExtractionService → raw text pulled from each source
   ├─② DocumentProcessor → text cleaned, word/char count added
   ├─③ ChunkingService   → text split into ~3000 token chunks
   ├─④ AIService         → each chunk sent to Groq, notes returned
   ├─⑤ MarkdownRenderer  → chunks joined into one big Markdown
   └─⑥ ExportService     → saved to outputs/notes.md
   │
   ▼
Flask sends notes.md as a download
```

---

## What's NOT done yet

- **`SYSTEM_PROMPT` is empty** — this is probably the most important thing to tackle next. Without clear instructions, the AI will do its best but won't produce consistent, well-structured notes. This prompt is where you'll define tone, depth, format, and what to focus on.
- **JSON parsing** — the AI returns a JSON string, but right now it's being saved raw (you can see this in `outputs/notes.md` — it includes the raw JSON code block). The next step is to *parse* that JSON, use the `KnowledgeDocument` model to hold it, and then render it properly into beautiful Markdown instead of dumping raw JSON.
- **`KnowledgeDocument` not used in the live pipeline** — the model exists but the pipeline doesn't create one yet. It will once JSON parsing is in place.
- **No styling on the frontend** — the UI works but looks like a plain HTML test page from 2003.
- **YouTube extractor** — the `extract_video_id_from_url` function referenced in tests doesn't appear to exist yet in `youtube_extractor.py` (the old version just read from `metadata["video_id"]`). This might be in progress.

---

## OOP/Code concepts introduced today

| Concept | Where | What it does |
|---|---|---|
| **Static method** | `SourceFactory` | A method on a class you can call without creating an object |
| **Composition** | `PipelineService`, `DocumentProcessor` | Classes that hold other classes as attributes to delegate work |
| **Regex (`re` module)** | `TextCleaner` | Pattern matching to find and replace messy text patterns |
| **JSON schema** | `schemas.py` | A contract that defines what structure data must follow |
| **Nested dataclasses** | `KnowledgeDocument` → `KnowledgeSection` → `KnowledgeBlock` | Classes that hold lists of other classes, creating a tree structure |
| **`pathlib.Path`** | `InputController`, `ExportService` | A cleaner, cross-platform way to handle file paths |

---

## 💬 My opinion on Day 2

**You did a lot in 6 hours. More than I expected for Day 2.**

The pipeline is end-to-end. That's not a small thing. Most beginners spend weeks getting to the point where a user action on a webpage causes data to flow through multiple services, get processed by an AI, and come back as a file download. You got there on Day 2. Credit where it's due.

**What I think is going really well:**

The architecture is holding up. The `PipelineService` as a central orchestrator is a good call — all the messy coordination is in one place, and each service still does only its own job. The `SourceFactory` is also a smart addition. That kind of "pre-sorter" keeps your controller clean and is very extensible — if you add a new file type later, you just add one line to the factory's dictionary.

**Where to be careful now:**

The biggest gap is the `SYSTEM_PROMPT`. Right now the AI is working blind. The notes it generates (look at `outputs/notes.md`) are literally just the JSON wrapped in a code block — it followed the schema but had no guidance on *how* to think about the content. Writing a strong system prompt is actually one of the highest-leverage things you can do in this project. That's what turns this from a "thing that calls an AI" into a "knowledge synthesis engine."

The second gap is JSON parsing. The pipeline's end product right now is a raw JSON string saved to a file — that's not the beautiful Obsidian-ready Markdown you're after. The `KnowledgeDocument` model is already waiting for it. Wiring that up is the next natural milestone.

**On the ChatGPT approach:** I can see from the `development log/` folder and the quality of the code that you're having real, structured conversations and not just copy-pasting. The comments in your code still show you explaining things back to yourself — `"Even tiny words like a and e have at least 1 cost"`, `"We get huge data back from Groq, choices is the list..."` — those are your own words. That habit is going to compound very quickly. Keep doing it. The gap between "following instructions" and "understanding architecture" closes every time you do that.

**One honest caution:** Six hours is great, but make sure you understand each file before you move on. The pipeline is built — but can you explain, from memory, why `PipelineService` exists separately from `ExtractionService`? Why the `SourceFactory` is separate from `InputController`? If you can answer those without looking, you're solid. If you can't, spend 10 minutes tomorrow re-reading Day 1 + Day 2 logs and tracing the flow. The architecture will reward you for understanding it deeply.

**Overall verdict:** Day 2 was a really strong session. You're past the "skeleton" phase and into the "it actually works" phase. The next session should be about *quality* — making the AI output genuinely good. That's the most creative part of the whole project. 🔥
