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
- Reference video: premium minimalist landing page animation (Apple/Linear/Framer style)
- Palette: cream `#F4EBDD` bg, white cards, near-black `#1A1A1A` headings, green `#2D6A4F` accent
- Font: Inter (Anthropic-like), JetBrains Mono for code
- Sections: Hero → How It Works → Supported Sources → Upload (drag-drop + URL textarea) → Output Preview → Stats → Footer
- Animations: scroll reveals (IntersectionObserver), floating cards, shimmer progress bar, smooth hover lifts
- JS: form submit handler (not button click) — prevents native submit, uses fetch + FormData → blob download
- If JS fails: native form submit falls back (form has action="/process", inputs have name="files"/"urls")

## Recent Fixes
- **Semicolon** (CSS): Missing `;` after `--ease` var made body invisible (opacity:0 animation broke)
- **Form submit** (JS): Changed from `button.click` to `form.submit` event — `e.preventDefault()` actually stops native submission now. Button also flashes (scale down) on click for visual confirmation.
- **stdout tee** (run.py): Wraps `sys.stdout`/`sys.stderr` with `_TeeStream` — every write flushes immediately + tees to `has.log` in project root
- **No reloader** (run.py): `use_reloader=False` prevents Flask child process from hiding output
- **Flush=True** added to key `print()` calls in pipeline_service.py, main.py, client.py, gemini_client.py, chunker.py, quality_gate.py

## Current State
- ✓ Frontend loads (cream bg, content visible, animations work)
- ✓ Backend pipeline runs end-to-end (generates `app/outputs/notes.md`)
- ✓ Form sends POST to /process with files + urls
- ✓ Terminal output goes to both console and `has.log`
- ⚠ API limits exhausted (Groq daily cap) — output quality degraded
- ⚠ Terminal printing still flaky on Windows (Flask + reloader issue)

## Output files
- Pipeline writes to `app/outputs/notes.md`
- Old test files in `notes_test/` (test1.md–test36.md) and `outputs/notes.md` (project root)
- Logs in `has.log`

## Key Files
- `run.py` — entry, stdout wrapper
- `app/templates/index.html` — full frontend (1172 lines, all inline CSS+JS)
- `app/routes/main.py` — routes
- `app/controllers/input_controller.py` — form parsing
- `app/services/pipeline_service.py` — pipeline orchestration
- `app/services/ai_service.py` — LLM orchestration
- `app/services/export_service.py` — writes `app/outputs/notes.md`
- `app/llm/client.py` / `gemini_client.py` — LLM clients
- `app/llm/prompts/` — all prompt templates
- `config.py` — model/provider config
