# Hybrid Assistant System (HAS)

Flask app that converts YouTube/PDF/DOCX/PPTX/webpages → beautiful Obsidian Markdown study notes using Groq/Gemini LLMs.

## Quick Start
```powershell
cd "C:\Users\ASUS\Documents\Python\Hopeful, Ambition, Scared"
.venv\Scripts\Activate.ps1
python run.py
# → http://127.0.0.1:5000
```

## Architecture
`app/routes/main.py` — Flask Blueprint (GET `/`, POST `/process`)
`app/templates/index.html` — premium frontend (cream/ivory, Inter font, green accents)
`app/controllers/input_controller.py` — parses files + urls from form, delegates to pipeline
`app/services/pipeline_service.py` — orchestration: extract → chunk → outline → (extract + teach) per topic → merge → render → quality gate → export
`app/services/ai_service.py` — LLM calls (GroqClient or GeminiClient)
`app/llm/prompts/` — base.py, outline.py, extraction.py, teaching.py, merge.py
`run.py` — entry point (debug=True, use_reloader=False)
`config.py` — LLM_PROVIDER, FAST_MODEL, REASONING_MODEL
`.env` — API keys

## UI / Frontend (index.html)
- Palette: cream `#F4EBDD` bg, white cards, near-black `#1A1A1A` headings, green `#2D6A4F` accent
- Font: Inter, JetBrains Mono for code
- Animations: scroll reveals (IntersectionObserver), floating cards, shimmer progress bar, smooth hover lifts
- JS: form submit handler (submit event, not click) — fetch + FormData → blob download
- Native form fallback if JS fails (form has action="/process", inputs have name="files"/"urls")

## Current Problem: ~1000 Word Ceiling

Output is ALWAYS ~1000 words regardless of input length (11 min, 1 hour, 3.5 hour all produce the same).

### What's Been Tried (all failed to break the ceiling)

**Round 1 — Gemini fallback:** `_run_teaching()` now tries OSS-120B → Llama-3.3-70B → Gemini 3.1 Flash Lite. All 20 topics survive rate limits now, but output still ~1000 words.

**Round 2 — Prompt contradiction fixes (7 edits across 3 files):**
- Removed anti-padding ("Do NOT pad") from teaching.py and merge.py
- Removed few-shot exemplar from teaching.py (was anchoring ~150 words)
- Changed "Cover only what the extracted knowledge actually contains" to "Use the extracted knowledge as your foundation. Expand on it..."
- Changed "coverage: rich — Stick closely... Don't supplement" to "Write thorough, detailed explanations... explain it fully"
- Removed "1-3 sentences max" cap from extraction.py
- Result: No change in output length.

**Round 3 — Full codebase audit:** All 47 Python files inspected. No hidden truncation, no hard caps, no content stripping found. Root cause is NOT in the infrastructure code.

### Debugging Tool Added

`app/services/ai_service.py` now prints each teaching section's word count BEFORE merge:
```
Topic 0 (Pre-training Data): 2450 chars / 380 words
```

This will tell us whether the bottleneck is at teaching (per-topic model won't expand) or merge (compresses aggressively).

### Next Session: First Task

**Read the console output from a run of the Karpathy (or any long) video.** Look for the "Topic X (...): ## chars / ## words" lines to determine:

- **If each topic is ~150-300 words:** Teaching is the bottleneck. The model fundamentally produces short output per topic. Options:
  1. Increase `max_tokens` multiplier (`knowledge_size // 8` → `knowledge_size // 4` or higher) in `_run_teaching()`
  2. Add explicit expansion instruction for "rich" coverage
  3. Use a more capable teaching model
  4. Merge extraction + teaching into one step

- **If each topic is ~400-800 words but final merge is ~1000:** Merge is the bottleneck. It compresses aggressively. Options:
  1. Remove "If material is thin, keep it concise" from merge.py
  2. Concatenate sections instead of merging (skip hierarchical merge for single-source)
  3. Increase merge `max_tokens` ceiling

## Key Files
- `run.py` — entry, stdout wrapper (use_reloader=False)
- `app/services/ai_service.py` — LLM orchestration, fallback chain, max_tokens
- `app/llm/prompts/teaching.py` — teaching prompt (338 lines after edits)
- `app/llm/prompts/merge.py` — merge prompt (389 lines)
- `app/llm/prompts/extraction.py` — extraction prompt (99 lines)
- `app/llm/prompts/base.py` — BASE_ROLE shared by all prompts
- `app/services/pipeline_service.py` — pipeline orchestration
- `config.py` — model config (GEMINI_FAST_MODEL, REASONING_MODEL, FAST_MODEL)
- `development log/Log 8.md` — full day's work log

## Model Architecture
- **FAST_MODEL** (default: `llama-3.3-70b-versatile` via Groq, or `gemini` keyword): Used for extraction, outline, repair
- **REASONING_MODEL** (default: `openai/gpt-oss-120b` via Groq): Used for teaching and merge
- **GEMINI_FAST_MODEL** (default: `gemini-3.1-flash-lite`): Used when `fast_model="gemini"` and as final fallback
- **Fallback chain (teaching):** OSS-120B → Llama-3.3-70B → Gemini 3.1 Flash Lite
- **Fallback chain (merge):** OSS-120B (3 retries) → Gemini 3.1 Flash Lite

## Groq Rate Limits
- OSS-120B: 8000 TPM (per minute)
- Llama-3.3-70B: 12000 TPM, 100K TPD (per day)
- Both exhaust quickly with 20 topics × 2-3K tokens each

## Output files
- Pipeline writes to `app/outputs/notes.md`
- Test files in `notes_test/` (test1.md–test47.md)
- Logs in `has.log` (stdout tee)

## Prompt Files (all checked and edited)
- `base.py` — "Prioritize clarity over brevity" (unchanged, is the anchor rule)
- `extraction.py` — removed "1-3 sentences max" cap, now says "Keep entries focused on one discrete concept each"
- `teaching.py` — removed anti-padding (x2), removed "Cover only what extracted", removed few-shot exemplar, fixed "rich" coverage to "write thorough, detailed explanations"
- `merge.py` — removed "Do NOT pad or invent", now says "Do NOT invent content not supported by the source sections"
- `outline.py` — clean, no changes
- `repair.py` — clean, no changes
- `study_notes.py` — unused
