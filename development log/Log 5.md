## Phase Overview

The project entered a quality-refinement phase. Infrastructure was stable but generated notes had structural issues: notation drift across sections, repeated explanations, inconsistent hyperparameter ranges, no diagrams, no callouts, and a textbook tone that didn't match the goal of personal study notes.

The focus shifted from "does the pipeline work?" to "does the output actually read like something you'd want to study from?"

---

# Problem Identified

After generating notes on Gradient Boosting for Regression (test13.md), a detailed evaluation revealed specific issues:

## 1. Notation Drift

The same mathematical concept appeared under four different names across sections: ŷ, f₀(x), F(xᵢ), and P₀. None were wrong individually, but nothing ever said "these are the same thing." The document read like four people wrote four sections independently.

## 2. Leaves vs Depth Used Interchangeably

Tree complexity was described as "4-32 leaves," then "4-8 leaves for gradual learning," then "8-32 leaves in practice," then suddenly "max depth = 3-5" with no line connecting leaf count to depth (a tree with depth 5 has up to 32 leaves — the missing link).

## 3. Stopping Criteria Numbers Conflicting

Different sections gave different ranges: "100-300 trees," "50-100 trees," "1000 trees," "hundreds to thousands." No reconciliation.

## 4. AdaBoost Comparison Repeated Three Times

The same AdaBoost vs Gradient Boosting explanation appeared in the intro, a dedicated section, and the misconceptions section — near-verbatim.

## 5. Structural Gaps

No Mermaid diagrams, no callout blocks, no internal wiki links, no LaTeX tables. The document was a wall of text with `---` separators.

---

# Root Cause Analysis

The pipeline generated each section independently via LLM, with only the previous section as context. The merge pass used a generic prompt ("combine these sections") without specific instructions to fix cross-section issues. The markdown renderer was a 3-line no-op.

```
Section 1 → LLM → Output
Section 2 → LLM → Output (only sees Section 1)
Section 3 → LLM → Output (only sees Section 2)
         ↓
    Merge (generic: "combine these")
         ↓
    Render (just joins with ---)
```

---

# Major Changes Made

## 1. Merge Prompt Overhaul (merge.py)

The most impactful change. The merge prompt was rewritten with explicit instructions:

- **Notation Unification**: Pick one symbol per concept and apply it everywhere.
- **Number Consistency**: Reconcile conflicting hyperparameter ranges; explain conditional differences.
- **Deduplication with Wiki Links**: Keep the best version of repeated explanations, replace others with [[#Exact Heading Name]].
- **Mermaid Diagrams**: Examples for flowcharts (iterative loops), graph comparisons (AdaBoost vs GB), and xychart-beta (function curves).
- **Obsidian Callouts**: [!note], [!tip], [!warning], [!example] blocks to break up walls of text.
- **LaTeX Tables**: Convert function comparison tables to proper LaTeX with \begin{array}.
- **Flow & Transitions**: Rewrite section openings to connect to previous sections.

Fixed Python string escaping issues — the prompt uses LaTeX examples which conflicted with f-string interpolation. Switched from f-string to concatenation to avoid backslash and curly-brace conflicts.

## 2. Teaching Prompt Rewrite (teaching.py)

Changed the tone from:
> "Write like a textbook written by an excellent professor."

to:
> "Write like you're explaining this to a friend over coffee."

Added instructions for:
- Mermaid diagrams (0-2 per section)
- Obsidian callouts (0-2 per section)
- Internal wiki links [[#Exact Heading]] for cross-referencing
- First-person voice ("Here's how I think about this")
- Analogies and everyday comparisons

## 3. Markdown Renderer (markdown_renderer.py)

Added post-processing:
- LaTeX cleanup (strips stray `\)`, fixes double-escaped delimiters)
- Collapses 3+ blank lines to 2

## 4. Rate Limiter (ai_service.py)

Added TPM tracking with a rolling 60-second window. API calls now delay to stay under the 6000 TPM limit. Tokens are tracked via usage metadata from API responses.

## 5. Token Usage Tracking (client.py + models.py)

Both GroqClient and GeminiClient now extract prompt_tokens, completion_tokens, and total_tokens from API responses. LLMResponse gained an optional `usage` dict field.

## 6. Gemini Client (gemini_client.py)

Created a new client for Google AI Studio API with the same interface as GroqClient:
- `generate(request: LLMRequest, model: str) -> LLMResponse`
- Uses `google-genai` SDK
- Same tenacity retry pattern
- Strips <think> tags

## 7. Provider Switching (ai_service.py + config.py)

AIService now checks `Config.LLM_PROVIDER` to choose between GroqClient and GeminiClient. Added `LLM_PROVIDER` env var to config (defaults to "groq").

## 8. Outline Prompt Refinement (outline.py)

Changed from vague "Prefer fewer sections" to concrete:
- "Aim for 3-5 topics. No more than 6."
- Explicit merge guidance (Motivation+Intuition together, Mechanism+Example together)
- Bad example (8 micro-topics) vs good example (3 merged topics)

## 9. Parallel Extraction (ai_service.py)

Rewrote generate_from_chunks with two phases:
- Phase 1: All extraction calls fire in parallel via ThreadPoolExecutor(max_workers=3)
- Phase 2: Teaching calls remain sequential (each depends on previous_notes)

Added threading.Lock to TPM tracker for thread safety.

---

# Provider Experiments

## Gemini 3 Flash Preview

Switched to Gemini via AI Studio. First run succeeded for section generation but hit the model's 20 requests/day free quota halfway through. The merge call also failed.

Key learning: Gemini's free tier is too restrictive for this workflow. Each run burns ~12 requests (outline + extractions + teachings + merge), meaning only 1-2 runs per day.

## Return to Groq

Reverted to Groq's qwen/qwen3-32b. The 6000 TPM limit is more usable — no daily cap, just a per-minute throttle that recovers naturally.

---

# Estimated Performance

Before any changes: 6-min video → ~10 min processing.
After parallel extraction + merged outline + Groq: 16-min video → ~3.5 min estimated.

---

# Current Status

Completed:
- ✅ Merge prompt with notation unification, diagrams, callouts, LaTeX tables
- ✅ Teaching prompt with friendly tone, analogies, diagrams, callouts, wiki links
- ✅ Markdown renderer post-processing
- ✅ TPM rate limiter with token tracking
- ✅ Gemini client implementation
- ✅ Provider switching architecture
- ✅ Outline prompt with concrete topic limits
- ✅ Parallel extraction phase

Remaining:
1. Further teaching prompt refinement
2. Few-shot examples in prompts
3. Evaluation framework for output quality
4. Unique output filenames in export
