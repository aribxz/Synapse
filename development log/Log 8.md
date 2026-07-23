# Day 8 — The 1000-Word Ceiling Battle

**Phase:** Output Quality Debugging


**Focus:** Fixing the hard ~1000-word ceiling on output length regardless of input size (14 min video, 1 hour, 3.5 hour lecture all produced identical word counts).

---

# Overview

The pipeline was working end-to-end but consistently produced ~1000 words of output. A 3.5-hour Karpathy lecture produced the same word count as an 11-minute video. The user reported this problem across multiple tests (test33 through test47), with the 1031-word output becoming a hard ceiling.

The day was spent chasing this ceiling through three rounds of fixes:
1. Adding Gemini as a 3rd-tier fallback for teaching (rate limits were dropping topics)
2. Removing contradictory anti-expansion signals from prompts (7 edits across 3 files)
3. Full source code audit of all 47 Python files

None of these fixed the 1000-word ceiling.

---

# Round 1: Gemini Fallback for Teaching

**Problem:** The teaching phase had only two fallback tiers — OSS-120B (8000 TPM) → Llama-3.3-70B (100K TPD). Both exhausted their Groq limits during a 20-topic run, causing 11 of 20 topics to silently fail. Only 8 topics survived → merge had thin input → 1031 words output.

**Fix:** Added Gemini 3.1 Flash Lite as a third fallback tier in `_run_teaching()`:
```
OSS-120B → Llama-3.3-70B → Gemini 3.1 Flash Lite
```

**Files:**
- `app/services/ai_service.py` — `_run_teaching()` now tries 3 models before failing

**Result:** All 20 topics now complete. But output was still ~1000 words. The rate limit fix was necessary but not sufficient.

---

# Round 2: Prompt Contradictions

**Problem:** The prompts had multiple contradictory instructions that suppressed output length. The teaching/merge prompts actively discouraged length while the base prompt said "Prioritize clarity over brevity."

**Contradictions found (all 8 prompt files inspected):**

| Contradiction | Location | Base Says | Prompt Says |
|---|---|---|---|
| Anti-padding | `teaching.py:248` | Prioritize clarity over brevity | Do NOT pad or invent content to fill space |
| "Cover only" | `teaching.py:248` | Prioritize clarity over brevity | Cover only what the extracted knowledge actually contains |
| Rich coverage | `teaching.py:262` | Prioritize clarity over brevity | Stick closely... Don't supplement beyond it |
| Exemplar anchor | `teaching.py:279-328` | Prioritize clarity over brevity | ~150 word output example |
| Anti-padding | `merge.py:19` | Prioritize clarity over brevity | Do NOT pad or invent content to fill space |
| 3-sentence cap | `extraction.py:73` | Prioritize clarity over brevity | Keep entries concise (1-3 sentences max per entry) |

**7 edits applied across 3 files:**

| File | Change |
|---|---|
| `teaching.py:248` | `Do NOT pad or invent` → `Do NOT invent` (removed anti-padding) |
| `teaching.py:248` | `Cover only what the extracted knowledge` → `Use the extracted knowledge as your foundation. Expand on it with clear explanations` |
| `teaching.py:254` | `Do not pad the notes with outside documentation knowledge` → `Do not present outside knowledge as if it were part of the source` |
| `teaching.py:262` | `coverage: rich — Stick closely... Don't supplement` → `Write thorough, detailed explanations... explain it fully` |
| `teaching.py:279-328` | Removed entire FEW-SHOT EXEMPLAR section (was anchoring ~150 words) |
| `merge.py:19` | `Do NOT pad or invent` → `Do NOT invent` (removed anti-padding) |
| `extraction.py:73` | `Keep entries concise (1-3 sentences max)` → `Keep entries focused on one discrete concept each` |

**Result:** Output still ~1000 words. Prompt changes had no measurable effect on output length.

---

# Round 3: Full Codebase Audit

**Action:** Read all 47 Python files in the project looking for hidden truncation, hard caps, or any code that could limit output length.

**Files checked and cleared:**
- `app/__init__.py` — simple Flask setup
- `app/routes/main.py` — streams output, no caps
- `app/controllers/` — form parsing, no truncation
- `app/services/pipeline_service.py` — orchestration, no caps
- `app/services/ai_service.py` — LLM orchestration (already modified)
- `app/services/quality_gate.py` — lints + repairs individual blocks only (mermaid/wikilinks)
- `app/services/export_service.py` — simple file write
- `app/rendering/markdown_renderer.py` — formatting fixes only (heading demotion, math delimiters, wiki-link fuzzy matching), no content stripping
- `app/rendering/linter.py` — lint only, no content modification
- `app/chunking/chunker.py` — 1200-token chunk limit, doesn't discard
- `app/ingestion/*.py` — extraction routing, clean
- `app/models/*.py` — data models, clean
- `app/processing/*.py` — text cleaning (whitespace only), token estimation
- `app/llm/*.py` — clients, models, parsers — all clean
- `config.py`, `run.py` — clean

**No truncation found anywhere in the codebase.**

---

# The Teaching max_tokens Calculation

The `max_tokens` for each teaching call is calculated dynamically:

```python
req.max_tokens = min(4096, max(1500, 1500 + knowledge_size // 8))
```

Where `knowledge_size` is the JSON length of the extracted knowledge dict (minus connections). For typical extraction data (2000-4000 chars), this gives ~1750-2000 max tokens per topic — enough for ~1300-1500 words. The model doesn't use this budget.

---

# Current Hypothesis

Two competing theories for the 1000-word ceiling:

**Theory A — Teaching Bottleneck:** The teaching model fundamentally produces ~150-300 words per topic regardless of prompt instructions. 20 topics × 200 words = 4000 words input to merge → merge stitches and compresses to ~1000.

**Theory B — Merge Bottleneck:** The teaching model produces adequate content (400-800 words per topic) but the merge model aggressively compresses it during the stitching pass, either because the merge prompt still has length-suppressing signals or because the model inherently summarizes.

**Debug tool added:** A one-line print in `generate_from_chunks()` that logs each teaching section's character and word count before passing to merge:

```python
tw = len(teaching_results[idx].split())
print(f"  Topic {idx} ({outline[idx].title}): {len(teaching_results[idx])} chars / {tw} words", flush=True)
```

This will reveal which theory is correct.

---

# What We Don't Know Yet

- Whether the teaching model produces 200 words or 500+ words per topic
- Whether the merge is compressing or just stitching
- Whether the problem is model capability or prompt structure
- What specific change would actually break the 1000-word ceiling

---

# Key Decisions Made Today

1. **Gemini fallback over Llama TPD tracking:** Rather than complex daily token tracking for Llama-3.3-70B (100K TPD), we added Gemini as a third fallback. Simpler code, same effect — all topics complete regardless of rate limits.

2. **Removed few-shot exemplar entirely (did not expand it):** The exemplar was the strongest length anchor. Expanding it would still anchor output — just at a slightly higher length. Removing it lets the model rely solely on the coverage-aware elaboration section, which scales naturally with content depth.

3. **Softened extraction cap instead of removing it:** Changed "1-3 sentences max" to "focused on one discrete concept" to allow longer entries when content merits it, while keeping the "don't merge concepts" signal.

4. **Chose debug logging over more speculative fixes:** After 7 prompt edits failed to change output, we added a measurement point rather than guessing at more changes. Without knowing where the compression happens, every fix is blind.

---

# Files Modified Today

| File | Changes |
|------|---------|
| `app/services/ai_service.py` | `_run_teaching()` — added 3rd fallback to Gemini; `generate_from_chunks()` — added debug word-count logging before merge |
| `app/llm/prompts/teaching.py` | 4 edits: removed anti-padding (x2), removed "Cover only what extracted", removed few-shot exemplar, fixed "rich" coverage guidance |
| `app/llm/prompts/merge.py` | 1 edit: removed "Do NOT pad or invent" → "Do NOT invent" |
| `app/llm/prompts/extraction.py` | 1 edit: removed "1-3 sentences max" cap |
| `AGENTS.md` | Updated with current context |
| `development log/Log 8.md` | This file |

---

# Next Session Start Points

1. **Read the debug log output** from the Karpathy lecture run to determine Theory A vs Theory B.

2. **If Theory A (teaching bottleneck):** Push per-topic word count up. Options:
   - Increase `max_tokens` multiplier (`knowledge_size // 8` → `knowledge_size // 4`)
   - Add explicit expansion instruction to teaching prompt for "rich" coverage
   - Use a more capable model for teaching (not OSS-120B via Groq)
   - Merge extraction + teaching into a single step so the model works directly from source text

3. **If Theory B (merge bottleneck):** Reduce merge compression. Options:
   - Remove "If material is thin, keep it concise" from merge prompt
   - Restructure merge to concatenate with smoothing rather than full rewrite
   - Skip merge entirely for single-source inputs
   - Increase merge `max_tokens` ceiling

4. **Long-term:** If neither theory pans out, investigate whether the extraction model (Gemini 3.1 Flash Lite or the configured FAST_MODEL) produces data too thin for the teaching model to expand on. Consider logging the extraction `coverage` field value to verify it's being set to "rich" for long-form content.

---

# Lessons Learned

1. **Prompt contradictions can be invisible until you trace the full chain.** "Cover only what extracted" in teaching + "1-3 sentences max" in extraction creates a double compression that no teaching fix can overcome alone.

2. **Removing constraints doesn't always change model behavior.** Even after removing anti-padding, few-shot exemplar, and "cover only" instructions, the model still defaults to ~200 words per topic. The model's training data and inherent behavior may be stronger than any prompt signal.

3. **Always measure before fixing.** I spent hours on prompt edits without first measuring where the compression actually happens. The debug logging should have been added in Round 1, not Round 4.

4. **The Groq TPM/TPD rate limits are the wrong thing to optimize.** Even with all topics completing via Gemini fallback, output length didn't increase. Rate limits were a distraction — the real problem is output length, not topic count.
