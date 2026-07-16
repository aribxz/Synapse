# StudyScore (Project: "Hopeful, Ambition, Scared") — Full Context Handoff

> **Purpose**: This document gives a fresh chat session everything needed to understand the project, its philosophy, current architecture, and the prioritized fix plan. Paste this into a new conversation and the assistant will have full context.

---

## 1. PROJECT PHILOSOPHY & GOAL

**What we're building**: A Flask web app that converts YouTube videos, PDFs, DOCX, PPTX, and webpages into **beautiful Obsidian Markdown study notes** — friendly, conversational, analogy-driven, genuinely useful for studying. Not textbook garbage.

**The north star**: Automate what you currently do manually with Claude — generate notes that feel like *you* wrote them for *yourself*.

**Tone mandate**: "Write like you're explaining to a friend over coffee." Simple language. Analogies to everyday things. First-person okay ("Here's how I think about this"). Humor welcome. No "leveraging paradigms" or "utilizing methodologies." **Teach, don't summarize.**

**Quality bar**: Notes should rival hand-crafted Claude output — coherent structure, consistent notation, diagrams where helpful, callouts for key ideas, internal wiki-links instead of repetition.

---

## 2. ARCHITECTURE (Stable — Do Not Restructure)

```
app/
├── __init__.py              # Flask factory
├── controllers/
│   └── input_controller.py  # Thin: receives request, delegates to PipelineService
├── ingestion/
│   ├── router.py, registry.py
│   └── extractors/          # PDF, YouTube, DOCX, PPTX, Webpage
├── processing/
│   ├── document_processor.py # Cleanup, metadata, token estimation
│   ├── cleaners.py, metadata.py, token_estimator.py
├── chunking/                # Text splitting for LLM context limits
├── llm/
│   ├── client.py            # GroqClient
│   ├── gemini_client.py     # GeminiClient (identical interface)
│   ├── models.py            # LLMRequest, LLMResponse (+ usage tracking)
│   ├── prompt_builder.py    # Builds prompts for each stage
│   ├── outline_parser.py
│   ├── extraction_parser.py
│   ├── knowledge_models.py  # ExtractedKnowledge dataclass
│   └── prompts/
│       ├── base.py          # BASE_ROLE
│       ├── outline.py       # OUTLINE_PROMPT (aim for 3-5 topics)
│       ├── extraction.py    # EXTRACTION_PROMPT (JSON schema)
│       ├── teaching.py      # TEACHING_PROMPT (friendly tone, diagrams, callouts)
│       └── merge.py         # MERGE_PROMPT (notation unification, dedup, diagrams)
├── services/
│   ├── ai_service.py        # Orchestrates outline → extraction → teaching → merge
│   ├── pipeline_service.py  # Top-level orchestration
│   ├── extraction_service.py
│   ├── chunking_service.py
│   ├── export_service.py
│   └── quality_gate.py      # Linter + AI repair
├── rendering/
│   ├── markdown_renderer.py # Joins sections + LaTeX/Mermaid cleanup
│   └── linter.py            # MarkdownLinter for QualityGate
├── routes/
│   └── main.py              # Flask routes (/, /process)
├── templates/
│   └── index.html           # Bare-bones upload form
├── models/                  # KnowledgeSource, KnowledgeCollection, Enums
config.py                    # FAST_MODEL, LLM_PROVIDER, REASONING_MODEL
run.py                       # Entry point
.env                         # API keys
```

**Pipeline Flow**:
```
InputController → PipelineService
    → ExtractionService (extract text from sources)
    → DocumentProcessor (clean, metadata, token estimate)
    → ChunkingService (split into chunks)
    → AIService
        → Outline Generation (3-5 topics with roles)
        → For each topic:
            → Extraction Pass (structured JSON knowledge)
            → Teaching Pass (friendly markdown)
        → Merge Pass (unify notation, dedup, diagrams, callouts)
    → MarkdownRenderer (post-process LaTeX, Mermaid, fences)
    → QualityGate (lint + AI repair)
    → ExportService (write file)
```

**Provider Switching** (via `.env`):
- `LLM_PROVIDER=groq` or `gemini`
- `FAST_MODEL` = model for outline/extraction (e.g., `qwen/qwen3-32b`)
- `REASONING_MODEL` = model for teaching/merge (e.g., `openai/gpt-oss-120b`)
- `GROQ_API_KEY` or `GEMINI_API_KEY`

Groq: 6K TPM (qwen-32b), 8K (gpt-oss-120b), no daily cap.  
Gemini free tier: 20 req/day — too restrictive; currently using Groq only.

---

## 3. KEY ARCHITECTURAL DECISIONS (Lessons Learned)

1. **Outline-driven generation** — Chunking is an implementation detail; document structure comes from an LLM-generated outline with topic roles (Motivation, Intuition, Mechanism, Procedure, Example, Edge Case, Takeaway). This decouples input chunks from output sections.

2. **Extract → Teach two-pass** — One LLM call extracts structured knowledge (JSON); a second call teaches it. Prevents "summarize instead of teach" and preserves facts before phrasing.

3. **Merge pass owns continuity** — With `previous_notes` removed (see Fix 1.1), the Merge pass now carries full continuity weight: notation unification, dedup via wiki-links, consistent terminology, heading hierarchy.

4. **Parallel where independent** — Extraction runs in parallel (3 workers). Teaching will too (2 workers, per Fix 1.2). Merge is sequential (needs full doc view).

5. **Token budget is the binding constraint** — 6K TPM on Groq qwen-32b means every token counts. Minify JSON, drop `previous_notes`, right-size models per stage.

6. **Groundedness > fluency** — Empty sources must produce visible gaps, never hallucinated content. Coverage-aware elaboration (Fix 2.2) distinguishes "safe to elaborate" (well-established concepts) from "must stay grounded" (source-specific claims).

7. **Post-process, don't over-prompt** — Mermaid validation, LaTeX cleanup, fence stripping happen in `MarkdownRenderer`/`QualityGate`, not in prompts.

---

## 4. CURRENT STATE (As of Log 5 / studyscore_fixes_spec.md)

**What works end-to-end**: Multi-source ingestion → extraction → chunking → outline → per-topic extract+teach → merge → markdown → export. Tested on 3.5hr Karpathy lecture.

**Output quality issues driving the fix spec**:
- Notation drift (same concept: y-hat, f0(x), F(x), P0)
- Conflicting hyperparameter ranges (100-300 trees vs 50-100 vs 1000)
- Repeated explanations (AdaBoost vs GB 3x)
- No diagrams, no callouts, no wiki-links
- Mid-document truncation in merge (test11, test19)
- 413 errors from token bloat (previous_notes ~15K chars)
- 7-min latency from sequential teaching calls

---

## 5. PRIORITIZED FIX SPEC (From `studyscore_fixes_spec.md`)

> **Implement in order. Each item states problem, fix, and why — keep reasoning in comments where it affects future judgment calls.**

---

### PRIORITY 1 — TOKEN BUDGET (Fixes 413s, short output, 7-min latency)

#### 1.1 Drop `previous_notes` from Teaching Prompt
- **Where**: `AIService` / `PromptBuilder.build_teaching()`
- **Change**: Teaching calls become self-contained — send only Outline (small, fixed) + topic's `knowledge_JSON`. No prior sections.
- **Why**: `previous_notes` was the single largest token consumer (~15K+ chars), directly causing 413s. Continuity should come from Outline (scope coordination) and Merge (reconciliation), not rolling context. This is a *better* continuity mechanism, not a downgrade.
- **Unlocks**: Teaching calls now independent → can parallelize (1.2).

#### 1.2 Parallelize Teaching Pass
- **Where**: `AIService.generate_from_chunks()`
- **Change**: `ThreadPoolExecutor(max_workers=2)` for teaching (like extraction's 3 workers).
- **Caution**: Use 2 workers, not 3 — extraction's 3-worker burst already filled TPM window and triggered 15-60s cooldowns. Teaching payloads are heavier; same concurrency hits ceiling faster.

#### 1.3 Minify Knowledge JSON Serialization
- **Where**: `PromptBuilder.build_teaching()` → `json.dumps(asdict(knowledge), separators=(",", ":"))`
- **Why**: Free 10-20% token reduction, zero content loss. Whitespace costs tokens.

#### 1.4 Split Extraction Fields by Consumer Stage
- **Change**: 
  - **Teaching input** (keep): `concepts`, `definitions`, `mechanisms`, `algorithms`, `reasoning`, `intuition`, `why_it_matters`, `examples`, `important_details`, `common_misconceptions`, `prerequisites`, `formulas`, `pitfalls`, `summary`
  - **Merge input only** (move): `connections` (cross-topic links) — Merge owns cross-topic relationships.
- **Files**: `extraction.py` (schema), `knowledge_models.py` (dataclass), `extraction_parser.py`, `PromptBuilder` (separate payloads), `merge.py` (prompt).

#### 1.5 Verify Groq Per-Model TPM & Right-Size Models
- **Action**: Check `console.groq.com/docs/models` directly (lineup shifts often).
- **Last known**: `qwen/qwen3-32b` = 6K TPM (bottleneck). `openai/gpt-oss-120b` = 8K TPM. `llama-3.3-70b-versatile` ≈ 12K TPM if still live — verify.
- **Swap**: Use `FAST_MODEL` (cheaper/faster) for Outline + Extraction. Use `REASONING_MODEL` for Teaching + Merge. Update `config.py` and `AIService` accordingly.

#### 1.6 Investigate Groq Prompt Caching
- **Action**: Check if identical `TEACHING_PROMPT` system prompt qualifies as cached prefix. Groq docs: cached input tokens don't count toward TPM. If yes, reclaims ~1,500 tokens/call free. Verify exact invocation mechanics.

#### 1.7 Fix Chunk Token Estimator
- **Where**: `app/chunking/chunker.py`
- **Change**: Replace per-word `max(1, len(word)//4)` with single `len(full_chunk_text) // 4`.
- **Why**: Per-word rounds most English words to 0-1, systematically undercounting total tokens across a document.

---

### PRIORITY 2 — TRUST / GROUNDEDNESS (Prevents Silent Fabrication)

#### 2.1 Empty/Thin-Source Guard Clause
- **Where**: `ExtractionService` / `DocumentProcessor`
- **Change**: If extracted text < min threshold (e.g., 200 chars), mark source `FAILED` with error. Never reaches Outline/Teaching.
- **Output**: Visible "couldn't extract text from this file" placeholder in final doc — not silence, not fabrication.
- **Why**: Observed fully hallucinated RL guide from source the model itself identified as empty. Empty source = visible gap, never confident invention.

#### 2.2 Coverage-Aware Scoped Elaboration
- **Where**: Extraction schema + Teaching prompt
- **Add field**: `coverage: "thin" | "adequate" | "rich"` per topic (LLM-assessed from source material).
- **Teaching rules**:
  - Well-established domain concepts with one settled explanation → safe to elaborate even when `coverage: thin` (no real ambiguity).
  - Source-specific claims (instructor's examples, opinions, exact numbers, framings) → strictly grounded in extraction. Do not invent specifics.
- **Mark supplemented content**: `> [!info] General background, not covered in this specific source` — distinct from source-grounded prose.

#### 2.3 Grounding Check on Technical Specifics
- **Where**: Teaching prompt
- **Add**: "Only include specific parameters/technical details (named hyperparameters, library functions, exact numbers) that the source actually covered. Do not pad with outside documentation knowledge presented as if from the lecture."

---

### PRIORITY 3 — PROMPT-LEVEL CONTENT QUALITY

#### 3.1 No Meta-Commentary on Source Structure
- **Where**: Teaching prompt
- **Add**: "Never write sentences referencing 'this section,' 'the following sections,' 'the video,' or the source's own organization. Write the material itself, not commentary about the material's organization."

#### 3.2 Cap Analogy Density
- **Where**: Teaching prompt
- **Add**: "One strong analogy per major concept, not one per paragraph. Repeating the same comparison reworded is filler, not intuition."

#### 3.3 No Vague Pseudo-Intuition
- **Where**: Teaching prompt
- **Add**: "If extraction captured no real analogy from the source, either produce one concrete, simple, explicit comparison, or omit the analogy line entirely. A vague abstract restatement that sounds like intuition but isn't is worse than no analogy."

#### 3.4 Few-Shot Exemplar
- **Where**: Teaching prompt
- **Add**: 1-2 worked examples: `Input knowledge_JSON → Output Markdown` demonstrating why-first depth, analogies, callouts, wiki-links. Anchors quality better than instructions alone.

---

### PRIORITY 4 — MERGE PASS FIXES

#### 4.1 Fix Mid-Document Truncation
- **Where**: `AIService.merge_sections()`
- **Change**: Increase `max_tokens` headroom; verify scaling with doc length. If still overflows: hierarchical merge (merge groups of 2-4 sections, then merge those results) instead of one giant call.
- **Why**: Two test runs (test11, test19) cut off mid-sentence — systemic.

#### 4.2 Normalize Heading Hierarchy
- **Where**: Merge prompt + `MarkdownRenderer`
- **Change**: Merge: "Ensure combined sections share consistent heading depth (## for top-level, ### for subsections)." Renderer: post-process to fix mismatched depths.

#### 4.3 Explicit Terminology/Glossary Pass
- **Where**: Merge prompt
- **Add**: "Enforce consistent terminology and phrasing for the same concept throughout the merged document. This now carries more continuity weight since rolling context was removed (1.1)."

---

### PRIORITY 5 — FORMATTING HYGIENE

#### 5.1 Mermaid: Prevent → Validate → Don't Just Patch
- **Prompt constraint**: Node IDs = plain alphanumeric; all labels double-quoted; no parentheses or nested brackets in labels.
- **Post-generation gate**: Basic syntax sanity-check on Mermaid blocks. If invalid → strip diagram entirely (better no diagram than broken syntax crashing Obsidian).

#### 5.2 Strip Dead `mermaid.live` Image Links
- **Where**: `MarkdownRenderer`
- **Change**: Regex `!\[.*?\]\(https://mermaid\.live/.*?\)` → remove. Native ` ```mermaid ` block already renders in Obsidian.

#### 5.3 Strip Stray ` ```markdown ` Code Fences
- **Where**: `MarkdownRenderer._strip_fences()`
- **Confirm**: Catches all cases — still appearing in some outputs despite being "tried."

---

### HYGIENE (Parallel, Low Priority, Low Effort)
- `tenacity` retries for 429s (partially done — confirm coverage in `client.py` / `gemini_client.py`)
- Trim `requirements.txt`: remove unused `jupyter*`, `streamlit`, `pandas`, `xgboost`, `altair`, `pydeck`, `graphviz`, `ipykernel`, `matplotlib`, `scikit-learn` (if not imported anywhere)
- Write `README.md` (project overview, setup, architecture diagram, run instructions)
- Expand test coverage: outline parser, merge output structure, markdown renderer edge cases, extraction parser, teaching prompt few-shot

---

## 6. KEY FILES TO TOUCH (Reference Map)

| Fix Area | Primary Files |
|----------|---------------|
| 1.1, 1.2, 1.3, 1.4, 1.5, 1.7 | `ai_service.py`, `prompt_builder.py`, `chunker.py`, `config.py` |
| 1.4, 2.2 | `extraction.py`, `knowledge_models.py`, `extraction_parser.py`, `merge.py` |
| 1.6 | Research — Groq docs / API test |
| 2.1 | `extraction_service.py`, `document_processor.py`, `pipeline_service.py` |
| 2.2, 2.3, 3.1-3.4 | `teaching.py` |
| 4.1-4.3 | `ai_service.py` (merge), `merge.py`, `markdown_renderer.py` |
| 5.1-5.3 | `teaching.py`, `merge.py`, `markdown_renderer.py`, `quality_gate.py` |
| Hygiene | `requirements.txt`, `client.py`, `gemini_client.py` |

---

## 7. HOW TO RUN / TEST

```bash
cd "Documents/Python/Hopeful, Ambition, Scared"
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python run.py
# Visit http://localhost:5000 — upload PDF/YouTube URL → downloads notes.md
```

**Tests**:
```bash
python -m pytest tests/ -v
# Current: test_ai_service.py, test_pipeline_service.py, test_routes.py, test_youtube_extractor.py
```

**Key env vars** (`.env`):
```
LLM_PROVIDER=groq
FAST_MODEL=qwen/qwen3-32b
REASONING_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=your_key
```

---

## 8. DECISION LOG (For Future Maintainers)

| Decision | Rationale | Revisit If |
|----------|-----------|------------|
| Outline-driven (not chunk-driven) | Chunks are technical; document structure should be pedagogical | If outline quality degrades on new domains |
| Extract → Teach two-pass | Separates fact-preservation from teaching craft | If latency becomes unacceptable |
| Merge owns continuity (no rolling context) | Rolling context ballooned tokens; outline+merge scales better | If cross-section coherence suffers on very long docs |
| 2 workers for teaching (not 3) | Extraction's 3 already saturated TPM; teaching heavier | If Groq TPM limits increase |
| Coverage field LLM-assessed | More nuanced than heuristic length checks | If LLM misjudges coverage systematically |
| Few-shot in teaching prompt | Instructions alone don't anchor "why-first" depth | If quality plateaus — add more shots or move to fine-tune |
| Hierarchical merge if needed | Single-call merge truncates at scale | When doc > ~8 sections consistently |

---

## 9. IMMEDIATE NEXT STEPS (If Starting Fresh)

1. **Start P1.1-P1.4 together** — they're interdependent (drop prev_notes → parallelize → minify JSON → split fields). Do as one cohesive refactor.
2. **Verify model TPMs (P1.5)** — before finalizing which model runs Teaching/Merge.
3. **Run a full integration test** on a 15-20 min video after P1 — confirm 413s gone, latency ~3-4 min, output quality stable.
4. **Then P2** (trust) — guard clauses first, then coverage-aware teaching.
5. **P3-P5** can be done in parallel / any order — they're prompt tweaks and post-process fixes.

---

## 10. CONTEXT / HANDOFF NOTES

- **Project folder**: `C:\Users\ASUS\Documents\Python\Hopeful, Ambition, Scared\`
- **Dev logs**: `development log/Log 1-5.md` — detailed architectural evolution
- **Fix spec source**: `studyscore_fixes_spec.md` (this document's source of truth for priorities)
- **Preferred workflow**: Small incremental fixes > big refactors. Preserve architecture. Correctness + presentation craftsmanship over cleverness.

---

*End of context. You now have everything needed to continue development.*