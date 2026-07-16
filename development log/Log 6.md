# Day 6 — Quality Sprint & Rendering Fixes

**Phase:** Quality Refinement & Formatting Hygiene

**Focus:** Implementing the prioritized fix spec from studyscore_fixes_spec.md, fixing Mermaid rendering issues, and routing models correctly to avoid TPM limits.

---

# Overview

Day 5 ended with `test13.md` evaluation highlighting notation drift, conflicting numbers, repeated explanations, and a complete absence of diagrams, callouts, and wiki-links. The fix spec was written but not implemented.

Today we implemented the entire fix spec (P1-P5), tested the output (test24.md), found rendering issues, fixed those, switched models three times, and finally landed on a stable dual-Groq setup.

---

# Priority 1 — Token Budget (P1.1–P1.7)

## P1.1 — Dropped `previous_notes` from Teaching Prompt

**Problem:** `previous_notes` was carrying ~15K chars of prior sections into every teaching call. This was the single largest token consumer and directly caused 413 errors.

**Change:** Teaching calls are now self-contained — they receive only the outline (small, fixed) + the topic's extracted knowledge JSON. Continuity shifted to the Merge pass (notation unification, dedup, wiki-links). This also made teaching calls independent of each other, which unlocked parallelization (P1.2).

## P1.2 — Parallelized Teaching Pass

**Change:** Teaching now runs with `ThreadPoolExecutor(max_workers=2)`, same as extraction's 3 workers. Two workers instead of three because teaching payloads are heavier and three would saturate the TPM window faster.

## P1.3 — Minified Knowledge JSON

**Change:** `json.dumps(asdict(knowledge), separators=(",", ":"))` — free 10-20% token reduction by stripping whitespace.

## P1.4 — Split Extraction Fields by Consumer

**Change:** Previously, every extraction field went to both Teaching and Merge. Now `connections` (cross-topic links) is filtered out of Teaching input and passed only to Merge. Teaching gets: concepts, definitions, mechanisms, algorithms, reasoning, intuition, why_it_matters, examples, important_details, common_misconceptions, prerequisites, formulas, pitfalls, summary.

## P1.5 — Verified Groq TPMs + Model-Per-Stage Routing

**Action:** Checked Groq console. Real on_demand limits:
- `qwen/qwen3-32b`: 6K TPM
- `openai/gpt-oss-120b`: 8K TPM
- `llama-3.3-70b-versatile`: 12K TPM

Wired `FAST_MODEL` for outline/extraction, `REASONING_MODEL` for teaching/merge.

## P1.6 — Groq Prompt Caching

**Finding:** Caching works on `gpt-oss-*` models automatically (identical system prompt prefixes are cached). NOT supported on `qwen/qwen3-32b`. No changes needed.

## P1.7 — Fixed Chunk Token Estimator

**Change:** `len(word)//4 + 1` per word (was `max(1, len(word)//4)`). The old formula undercounted English words (most rounded to 0-1). The new formula adds +1 per word, producing more accurate estimates.

---

# Priority 2 — Groundedness (P2.1–P2.3)

## P2.1 — Empty-Source Guard

**Status:** Already existed in `extraction_service.py` (< 200 chars → FAILED). Pipeline also shows visible "could not extract text" placeholder. Verified, no changes needed.

## P2.2 — Coverage-Aware Elaboration

**Additions:**
- `coverage: str = "adequate"` field added to `ExtractedKnowledge` dataclass
- Extraction prompt schema now includes `coverage` (thin | adequate | rich) — LLM-assessed, not heuristic
- Teaching prompt has coverage-aware rules:
  - `rich`: stick strictly to extracted material
  - `adequate`: may add small background context
  - `thin`: standard domain knowledge may be elaborated with `> [!info]` attribution; source-specific claims must stay grounded

## P2.3 — Grounding Instruction

**Added to teaching prompt:** "Only include specific parameters, hyperparameters, library functions, or exact numerical values that the source actually covered."

---

# Priority 3 — Prompt Quality (P3.1–P3.4)

## P3.1 — No Meta-Commentary

**Added:** "Never write sentences referencing 'this section,' 'the following sections,' 'the video,' or the source's own organization."

## P3.2 — Cap Analogy Density

**Added:** "One strong analogy per major concept, not one per paragraph."

## P3.3 — No Vague Pseudo-Intuition

**Added:** "If extraction captured no real analogy, either produce one concrete explicit comparison or omit the analogy entirely."

## P3.4 — Few-Shot Exemplar

**Added:** A complete worked example (knowledge input → teaching output) demonstrating why-first structure, a single strong analogy (librarian), properly fenced Mermaid diagram, callouts, and a wiki-link. Anchors quality expectations better than abstract instructions.

---

# Priority 4 — Merge Pass (P4.1–P4.3)

## P4.1 — Merge max_tokens 4096 + Hierarchical Fallback

**Changes:** Merge `max_tokens` increased from default to 4096. Added hierarchical fallback for documents with >4 sections: merge in pairs, then merge the results. Prevents mid-sentence truncation that appeared in test11 and test19.

## P4.2 — Heading Hierarchy Normalization

**Post-process in `MarkdownRenderer._normalize_headings()`:** Demotes `#` to `##` if multiple top-level heads exist. Merge prompt also instructed to maintain consistent heading depth.

## P4.3 — Terminology Consistency

**Added to merge prompt:** "Enforce consistent terminology and phrasing for the same concept throughout the merged document."

---

# Priority 5 — Formatting Hygiene (P5.1–P5.3)

## P5.1 — Mermaid Validation

`QualityGate._validate_mermaid()` already existed. Enhanced to strip unbalanced bracket blocks.

## P5.2 — Strip Dead mermaid.live Links

`MarkdownRenderer._strip_mermaid_live_links()` — regex removes `![](https://mermaid.live/...)` image links. Native ` ```mermaid ` blocks already render in Obsidian.

## P5.3 — Enhanced Fence Stripping

`_strip_fences()` catches more stray ` ```markdown ` fence cases.

---

# Testing: test24.md

User tested the output of the complete fix spec on a YouTube video. Verdict: **"fairly satisfied"** — good length, acceptable generation time, but rendering issues in the markdown.

---

# Rendering Issues Found in test24.md

## Broken Mermaid Blocks
**Root cause:** `_strip_fences()` in `markdown_renderer.py` had a blanket `re.sub(r"```\n?", "", text)` that nuked ALL triple backtick fences from the document — including ` ```mermaid ... ``` ` blocks. The model WAS outputting proper fences, but they were stripped before `_fix_mermaid_nodes()` could process them.

**Output before fix:** `mermaid` on its own line (no backticks), followed by flowchart syntax — Obsidian doesn't render this as a diagram.

## Broken Wiki-Link
test24.md line 203: `[[#Baseline Dopamine Reset and Effusion-Reward Loop Strategies]]` — heading was actually "Baseline Dopamine Reset and Effort-Reward Loop Strategies (Procedure)". Link wouldn't resolve in Obsidian.

## Callout Formatting
The model wrapped `[!tip]` in bold markers: `> **[!tip]**` instead of Obsidian's `> [!tip]`.

---

# Rendering Fixes — Three-Layer Mermaid Defense

## Layer 1 — Blunt Fix (`markdown_renderer.py`)

Added `re.sub(r'\["([^"]*?)"\]', r'(\1)', block)` at the end of `_fix_block()`. Converts any remaining `["text"]` → `(text)` inside ` ```mermaid ` blocks. Catches all nested bracket variants including `Node[text["inner"]]` and xychart labels like `"f["f(z)"]"`.

## Layer 2 — Prompt Prevention (`teaching.py` + `merge.py`)

Added explicit anti-nesting constraints with good/bad examples:
```python
Bad:  H[Hidden Layer["Layer(s)"]]    ← nested brackets, breaks Mermaid
Bad:  A[Activation f["f(z)"]]        ← same
Good: H["Hidden Layer (Layer(s))"]   ← one bracket pair, content in quotes
```

## Layer 3 — Bracket Balance Gate (`quality_gate.py`)

Added unbalanced bracket detection to `_validate_mermaid()`. If `[` count ≠ `]` count in any ` ```mermaid ` block after all fixes, the entire block is stripped. This catches novel bracket variants that slip through both regexes and prompts.

---

# Additional Markdown Fixes

- **`_fix_callouts()`**: `re.sub(r'\*\*\[!(\w+)\]\*\*', r'[!\1]', text)` — strips `**` from `[!type]` markers
- **`_fix_wiki_links()`**: Fuzzy-matches `[[#link-text]]` against actual headings using word-overlap similarity (threshold 0.4). Fixes typos automatically.
- **`_wrap_naked_mermaid()`**: Pre-fence-stripping safety net that detects bare `mermaid\nflowchart...` patterns and wraps them with proper fences.

---

# Model Routing Saga

## Attempt 1: Gemini Flash-Lite (Outline + Extraction)
**Result:** 429 Quota Exhausted — free tier has 0 quota for `gemini-2.0-flash-lite`. The 250K TPM / 500 RPD the user mentioned requires paid tier.

## Attempt 2: Ollama (Fast Model)
**Result:** User didn't have Ollama setup. Client deleted.

## Attempt 3: Groq Dual-Model (Final)
**Final routing:**
| Stage | Model | TPM Limit |
|-------|-------|-----------|
| Outline | `llama-3.3-70b-versatile` | 12K |
| Extraction | `llama-3.3-70b-versatile` | 12K |
| Teaching | `openai/gpt-oss-120b` | 8K |
| Merge | `openai/gpt-oss-120b` | 8K |
| Repair | `llama-3.3-70b-versatile` | 12K |

---

# TPM Tracking Fixes

## Root Bug: Single Shared Window
The original `_wait_for_tpm()` used one `_tpm_window` list for all models. Extraction tokens (llama, 12K limit) were counted against teaching's (gpt-oss, 8K limit), causing 58-60 second false waits.

## Fix: Per-Model TPM Windows
TPM tracking now uses a dictionary of windows keyed by model name. Each model's token usage is tracked independently. `_wait_for_groq_tpm()` and `_track_groq_usage()` accept a `model` parameter and use the correct window.

## Import Order Bug
`config.py` was being imported before `client.py`'s `load_dotenv()` ran, so `os.getenv("FAST_MODEL")` returned the hardcoded default (`qwen/qwen3-32b`) instead of the `.env` value. Fixed by adding `load_dotenv()` directly in `config.py`.

---

# test26.md — Final Result

After all fixes, the pipeline produced a clean 190-line markdown document with:
- ✅ Properly fenced Mermaid diagrams (flowchart + xychart-beta)
- ✅ Correct Obsidian callouts (`> [!tip]`, `> [!warning]`, `> [!info]`, `> [!example]`)
- ✅ LaTeX math blocks with activation function table
- ✅ Internal wiki-links between sections
- ✅ Why-first structure with analogies (factory assembly line, LEGO plates)
- ✅ No meta-commentary, no textbook tone
- ✅ No 413 errors, no TPM breaches

---

# Files Modified Today

| File | Changes |
|------|---------|
| `app/services/ai_service.py` | Parallel teaching (2 workers), per-model TPM windows, routing logic, outline max_tokens |
| `app/llm/prompt_builder.py` | Minified JSON, connections filter, outline max_tokens=4096 |
| `app/llm/prompts/teaching.py` | Previous_notes removed, coverage-aware rules, grounding, analogy caps, few-shot exemplar, Mermaid constraints |
| `app/llm/prompts/extraction.py` | Added `coverage` field schema |
| `app/llm/prompts/merge.py` | Notation unification, heading hierarchy, terminology consistency, Mermaid constraints |
| `app/llm/prompts/outline.py` | Anti-reasoning instruction, max_tokens=4096 |
| `app/llm/knowledge_models.py` | Added `coverage: str = "adequate"` |
| `app/llm/client.py` | Fixed `<think>` regex to handle unclosed tags |
| `app/rendering/markdown_renderer.py` | `_wrap_naked_mermaid()`, `_fix_callouts()`, `_fix_wiki_links()`, `_strip_fences()` fix, `["..."]` → `(...)` blunt fix |
| `app/services/quality_gate.py` | Bracket balance validation |
| `config.py` | Added `load_dotenv()`, cleaned up model defaults |
| `app/llm/ollama_client.py` | Created then deleted |

---

# Lessons Learned

1. **Import order matters.** `load_dotenv()` must run before any `Config` class is defined. Putting it in `config.py` guarantees correct order regardless of import chain.

2. **Per-model TPM tracking is essential on multi-model pipelines.** Groq enforces per-model limits, not a global limit. Sharing a single TPM window across models causes false throttling.

3. **Prevention beats regex chasing.** The model keeps finding new ways to nest brackets in Mermaid labels (unquoted outer, quoted outer, xychart strings). Each new variant requires a new regex. The prompt constraint (Layer 2) and bracket-balance gate (Layer 3) are more sustainable than expanding regex patterns indefinitely.

4. **Blunt fixes are safe inside ` ```mermaid ` blocks.** `["text"]` → `(text)` is crude but can't escape the fenced block. Safer than trying to predict every bracket variant the model might generate.

5. **Free-tier LLM APIs are not viable for this workflow.** Each run burns ~10-15 requests. Gemini's 20 req/day free quota would allow ~1-2 runs. The 12K/8K TPM on Groq on_demand is tight but workable with proper throttling.

---

# Current Status

Completed:
- ✅ Entire fix spec (P1-P5) implemented
- ✅ Mermaid three-layer defense (blunt fix + prompt + gate)
- ✅ Callout, wiki-link rendering fixes
- ✅ Per-model TPM tracking
- ✅ Dual-model Groq routing (llama versatile + gpt-oss-120b)
- ✅ test26.md demonstrates all fixes working

Known remaining:
- TPM waits for gpt-oss-120b teaching calls can be 50-60s with 3 parallel topics
- The wiki-link fuzzy matcher uses simple word overlap; won't catch severe typos
- No unique filenames in export service (still overwrites notes.md)
