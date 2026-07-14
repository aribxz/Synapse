# Project Context

## Who you are

You're building a Flask web app that converts YouTube videos, PDFs, DOCX, PPTX, and webpages into beautiful Obsidian Markdown study notes. The goal is to automate what you currently do with Claude — generating notes that are friendly, conversational, analogy-driven, and genuinely useful for studying. Not textbook garbage.

## Your preferences

- **Tone**: Friendly, conversational, like explaining to a friend. Analogies and everyday comparisons. First-person is fine. No "leveraging paradigms" or "utilizing methodologies."
- **Code style**: Clean, minimal comments. Existing patterns are more important than introducing new ones.
- **Architecture**: Service-oriented. Controllers are thin. PipelineService orchestrates everything. Single responsibility per class.
- **You value**: Preserving existing architecture over rewriting. Small incremental fixes over big refactors. Correctness + presentation craftsmanship.

## Project structure

```
app/
├── __init__.py              # Flask factory
├── controllers/
│   └── input_controller.py   # Thin controller, delegates to PipelineService
├── ingestion/
│   ├── router.py, registry.py
│   └── extractors/           # PDF, YouTube, DOCX, PPTX, Webpage
├── processing/
│   ├── document_processor.py # Cleanup, metadata, token estimation
│   ├── cleaners.py, metadata.py, token_estimator.py
├── chunking/                 # Text splitting for LLM context limits
├── llm/
│   ├── client.py             # GroqClient
│   ├── gemini_client.py      # GeminiClient (same interface)
│   ├── models.py             # LLMRequest, LLMResponse (+ usage tracking)
│   ├── prompt_builder.py     # Builds prompts for each stage
│   └── prompts/
│       ├── base.py           # BASE_ROLE
│       ├── outline.py        # OUTLINE_PROMPT (aim for 3-5 topics)
│       ├── extraction.py     # EXTRACTION_PROMPT (JSON schema)
│       ├── teaching.py       # TEACHING_PROMPT (friendly tone, diagrams, callouts)
│       └── merge.py          # MERGE_PROMPT (notation unification, dedup, diagrams)
├── services/
│   ├── ai_service.py         # Orchestrates outline → extraction → teaching → merge
│   ├── pipeline_service.py   # Top-level orchestration
│   ├── extraction_service.py, chunking_service.py, export_service.py
├── rendering/
│   └── markdown_renderer.py  # Joins sections + LaTeX cleanup post-processing
├── routes/
│   └── main.py               # Flask routes (/, /process)
├── templates/
│   └── index.html
config.py                     # FAST_MODEL, LLM_PROVIDER, etc.
run.py                        # Entry point
.env                          # API keys and config
```

## Pipeline flow

```
InputController → PipelineService
    → ExtractionService (extract text)
    → DocumentProcessor (clean)
    → ChunkingService (split)
    → AIService
        → Outline Generation (3-5 topics)
        → For each topic:
            → Extraction Pass (structured JSON)
            → Teaching Pass (friendly markdown)
        → Merge Pass (unify notation, dedup, add diagrams/callouts)
    → MarkdownRenderer (post-process)
    → ExportService (write file)
```

## Provider switching

Set in `.env`:
- `LLM_PROVIDER=groq` or `gemini`
- `FAST_MODEL` = model name string
- `GROQ_API_KEY` or `GEMINI_API_KEY`

Groq: qwen/qwen3-32b (6000 TPM limit, no daily cap). Gemini: gemini-3-flash-preview (20 req/day free tier — very restrictive).

Both clients have identical `generate(self, request: LLMRequest, model: str) -> LLMResponse` interface. Switching happens in `AIService.__init__` based on `Config.LLM_PROVIDER`.

## What we built last session (Log 5)

- Evaluated test13.md (Gradient Boosting) — found notation drift, repeated explanations, conflicting numbers, no diagrams/callouts
- Overhauled merge.py — specific instructions for notation unification, dedup with [[#wiki links]], Mermaid diagrams, Obsidian callouts, LaTeX tables
- Rewrote teaching.py — friendly/conversational tone, diagrams, callouts, wiki links
- Enhanced markdown_renderer.py — LaTeX cleanup post-processing
- Added token usage tracking to LLMResponse and both clients
- Created gemini_client.py with same interface as GroqClient
- Added provider switching in AIService via Config.LLM_PROVIDER
- Refined outline.py — concrete "aim for 3-5 topics" with merge guidance
- Added parallel extraction phase (ThreadPoolExecutor, 3 workers) in ai_service.py
- Added threading.Lock to TPM tracker for thread safety
- Discovered Gemini free tier too restrictive (20 req/day)
- Switched back to Groq

## Known issues / TODOs

- Teaching prompt could still use few-shot examples
- No evaluation framework for output quality
- ExportService overwrites notes.md — needs unique filenames
- Chunking is basic word-count, could be paragraph-aware or semantic
- Frontend is intentionally primitive (not the bottleneck)
- Groq TPM limit means ~30-40s cooldown after parallel extraction burst

## How to pick up

Read `development log/Log 5.md` for full session details. Then read the specific file you need to modify. Always check the existing patterns first. Run with `.venv\Scripts\python run.py`.
