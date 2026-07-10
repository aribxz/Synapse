This document continues from the previous revision summary. The previous summary ended roughly around the point where all extractors (PDF, DOCX, PPTX, Webpage, YouTube) had been implemented and the extraction pipeline was functional.

From this point onward, the project shifted from **"extracting information"** to **"building a complete AI-powered document processing pipeline."**

---

# Phase Shift

Originally, the project consisted of individual components:

```
Input

↓

Extraction

↓

Output
```

This gradually evolved into a proper software architecture.

Instead of building isolated scripts, we started building a layered application.

The biggest architectural decision was introducing a **Pipeline Service**.

Instead of controllers manually calling five or six services, all orchestration would happen in one place.

Controllers should not know business logic.

Controllers should only receive input and delegate work.

This became an important design principle throughout the project.

---

# Input Layer

The Input Layer became responsible for collecting every source the user provides.

The application now supports:

- PDF
- DOCX
- PPTX
- YouTube URLs
- Webpage URLs

The InputController builds a KnowledgeCollection containing every source.

This means that the entire application is designed around **multi-source input**, not just single documents.

That decision was made intentionally because the long-term goal is to support things like:

- multiple PDFs
- multiple YouTube lectures
- documentation plus slides
- mixed educational sources

inside one request.

---

# InputController

Location

```
app/controllers/input_controller.py
```

Responsibilities:

Receive browser requests.

Create uploads folder if necessary.

Secure uploaded filenames.

Save uploaded files.

Collect URLs.

Convert everything into KnowledgeSource objects using SourceFactory.

Build one KnowledgeCollection.

Pass the collection to PipelineService.

Return the generated output file.

Important implementation details:

Uses

```
secure_filename()
```

to prevent malicious filenames.

Creates

```
uploads/
```

automatically using

```
Path.mkdir(exist_ok=True)
```

instead of assuming it already exists.

Uses

```
request.files.getlist("files")
```

because multiple uploads are supported.

Uses

```
request.form.get("urls")
```

to support multiple URLs.

Each URL becomes a KnowledgeSource.

---

# SourceFactory

SourceFactory had already existed earlier.

Its responsibility became even more important.

Instead of InputController containing a large

```
if pdf

if docx

if pptx

...
```

block,

SourceFactory became responsible for creating the appropriate KnowledgeSource.

InputController therefore does not care what the input actually is.

It simply asks SourceFactory to create the correct object.

This keeps responsibilities separate.

---

# Pipeline Service

This became the heart of the application.

Location

```
app/services/pipeline_service.py
```

This class exists only to orchestrate the workflow.

It does not perform extraction itself.

It does not process text.

It does not chunk.

It simply coordinates every service.

Current workflow:

```
KnowledgeCollection

↓

ExtractionService

↓

DocumentProcessor

↓

ChunkingService

↓

AIService

↓

MarkdownRenderer

↓

ExportService

↓

Return output file
```

PipelineService owns instances of:

ExtractionService

DocumentProcessor

ChunkingService

AIService

MarkdownRenderer

ExportService

Its process() function performs every stage in order.

For each KnowledgeSource inside the collection:

Extract text.

Process text.

Split into chunks.

Generate AI output for every chunk.

Collect generated sections.

Render them into one Markdown string.

Export Markdown.

Return the exported file path.

This became the application's central orchestration layer.

---

# ExtractionService

No major architectural changes occurred here.

Its responsibility remained:

Receive KnowledgeCollection.

Loop through every source.

Select the correct extractor using ExtractorRegistry.

Update each KnowledgeSource.

Return the updated collection.

It continues to work independently of AI.

---

# DocumentProcessor

A new processing layer was introduced.

Purpose:

Prepare extracted text before AI.

Examples:

Whitespace cleanup.

Basic preprocessing.

Future improvements.

The important architectural decision:

Extraction should only extract.

Processing should only process.

Neither service should perform the other's responsibilities.

---

# Chunking

This was the biggest new subsystem.

Reason:

LLMs cannot reliably process extremely large lectures in one request.

Instead of treating the document as one huge string, it becomes multiple chunks.

Current implementation:

Folder:

```
app/chunking/
```

Contains:

Chunk

Chunker

ChunkingService

---

## Chunk

Chunk is a dataclass.

Fields:

id

text

estimated_tokens

Purpose:

Represent one piece of a document.

This object becomes the unit passed to AIService.

---

## Chunker

Chunker performs the actual splitting.

Current algorithm:

Split text into words.

Estimate token count.

When estimated tokens exceed max_tokens:

Create a Chunk.

Start another chunk.

Current estimation:

```
estimated = max(1, len(word)//4)
```

This is intentionally simple.

Future improvements:

Paragraph-aware chunking.

Overlap.

Semantic chunking.

Adaptive chunk sizes.

---

## ChunkingService

Acts as the interface between PipelineService and Chunker.

PipelineService never interacts with Chunker directly.

It only calls:

```
ChunkingService.process(source)
```

This maintains separation of responsibilities.

---

# AI Layer

A dedicated LLM folder was introduced.

Location

```
app/llm/
```

Contains:

client.py

models.py

prompts.py

prompt_builder.py

schemas.py

Originally the plan involved strict JSON generation.

Later, we decided that V1 should prioritise **note quality** over output structure. The JSON work proved that the model could follow structured instructions, but the product's real value is high-quality Markdown. The idea of JSON as an intermediate representation is deferred, not abandoned.

---

## client.py

Purpose:

Communicate with Groq.

Nothing else.

Responsibilities:

Load API key.

Create Groq client.

Send prompt.

Receive response.

Return LLMResponse.

No application logic exists inside this file.

---

## prompts.py

Contains reusable prompt templates.

Current version is minimal.

Long-term plan:

Study Notes.

Technical Reference.

Exam Preparation.

Quick Revision.

Prompt versioning.

---

## prompt_builder.py

Receives raw text.

Builds an LLMRequest.

Combines:

System prompt.

User prompt.

Schema or formatting instructions.

Returns one prompt object.

PipelineService never builds prompts manually.

---

## models.py

Introduced two dataclasses.

LLMRequest.

LLMResponse.

Reason:

Avoid passing random dictionaries and strings throughout the application.

---

# AIService

Location

```
app/services/ai_service.py
```

Purpose:

Bridge the application and the LLM layer.

Responsibilities:

Receive chunks.

Loop over chunks.

For each chunk:

Build prompt.

Call Groq.

Collect response.

Return generated sections.

The important architectural decision:

AIService knows about chunks.

It does NOT know about PDFs.

It does NOT know about YouTube.

It does NOT know about Flask.

---

# Markdown Renderer

Location

```
app/rendering/markdown_renderer.py
```

Purpose:

Combine generated sections.

Current implementation:

Joins sections using separators.

Current implementation is intentionally minimal.

Future:

Proper Obsidian formatting.

Frontmatter.

Automatic TOC.

Mermaid.

LaTeX.

Callouts.

Admonitions.

---

# ExportService

Location

```
app/services/export_service.py
```

Purpose:

Write Markdown to disk.

Current behaviour:

Creates

```
outputs/
```

if necessary.

Writes

```
notes.md
```

Returns file path.

Future improvement:

Generate unique filenames instead of overwriting notes.md.

---

# Frontend

Current frontend is intentionally primitive.

```
templates/index.html
```

Contains:

File upload.

Multiple file support.

URL textarea.

Submit button.

Nothing more.

Reason:

Frontend is not the bottleneck.

Quality of note generation is.

The frontend currently acts only as an integration testing interface.

---

# Flask Routes

Current routes:

```
/
```

Returns index.html.

```
/process
```

Receives upload.

Delegates everything to InputController.

Returns

```
send_file(...)
```

which downloads notes.md.

Temporary testing routes such as `/test-ai` and `/test-chunk` were created during development. Once their respective components were validated, they became unnecessary. The direction is to remove or keep them only for internal debugging so the application stays focused on the real end-to-end flow.

---

# End-to-End Milestone

A complete integration test was successfully performed.

Process:

Upload PDF.

↓

Extraction succeeds.

↓

Processing succeeds.

↓

Chunking succeeds.

↓

Groq generates output.

↓

MarkdownRenderer combines sections.

↓

ExportService writes file.

↓

Browser downloads notes.md automatically.

The downloaded file contained valid AI-generated output.

This officially marked the completion of the first end-to-end version of the product.

---

# Architectural Principles Established

Several principles emerged during this phase and should continue guiding development:

- **Single Responsibility:** Each class should do one thing well.
- **Controller Thinness:** Controllers validate and delegate; they do not orchestrate business logic.
- **Pipeline Orchestration:** Multi-step workflows belong in `PipelineService`.
- **Dependency Separation:** Services should depend only on what they need. For example, `AIService` works with chunks, not PDFs or Flask.
- **Incremental Evolution:** Improve existing components instead of redesigning the architecture every few prompts.
- **Maintainability Over Cleverness:** Prefer straightforward, readable code to overly abstract solutions.

---

# Lessons Learned

Several important lessons came out of this phase:

1. **Prototype the highest-risk assumption first.** Proving that a free Groq model could generate structured output was more valuable than building more infrastructure.
2. **Separate concerns early.** Having distinct extraction, processing, chunking, AI, rendering, and export layers made integration much cleaner.
3. **Avoid premature optimization.** The current chunker and renderer are intentionally simple because they solve today's problem and leave room for future improvements.
4. **Architecture should stabilize.** Repeated redesigns slow progress. Once a sound structure exists, development should focus on completing features and improving quality.

---

# Current Locked Roadmap

The infrastructure phase is considered complete for Version 1.

Future work should follow this order:

1. Improve the system prompt.
2. Create prompt templates (Study Notes, Technical Reference, Exam Preparation, Quick Revision).
3. Generate polished Obsidian-ready Markdown instead of basic output.
4. Improve chunk continuity (carry context between chunks).
5. Add a merge pass that combines chunk-level notes into one coherent document.
6. Improve the frontend with the polished StudyScore-style interface.
7. Add quality evaluation, testing, and deployment improvements.

---

# Final State at the End of This Phase

The project is no longer a collection of scripts.

It is now a modular software application with a defined architecture.

The next stage is **not** primarily software engineering—it is **knowledge engineering**.

From this point onward, the success of the product depends less on creating new classes and more on producing notes that genuinely rival your current Claude workflow. That means prompt design, chunk orchestration, Markdown quality, and AI behavior become the central focus of development.