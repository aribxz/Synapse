# StudyScore — Consolidated Fix Spec

Implement in the priority order given. Each item states the problem, the fix, and why — keep the reasoning in comments where it affects a future maintainer's judgment call.

---

## Priority 1 — Token budget (fixes 413s, short output, AND the 7-min latency problem)

### 1.1 Drop `previous_notes` from the Teaching prompt entirely
- **Where:** `AIService` / Teaching pass call construction.
- **Change:** Each per-topic Teaching call becomes self-contained — send only the outline (fixed, small size) + that topic's `knowledge_JSON`. Do not send prior sections' generated text.
- **Why:** `previous_notes` was ballooning to 15K+ chars and is the single largest token consumer, directly causing 413s. Continuity should come from the Outline (coordination — sections don't overlap in scope) and the Merge pass (reconciliation — consistent terminology/tone), not from each section reading the last one. This is a strictly better continuity mechanism, not a downgrade.
- **Unlocks:** Since Teaching calls no longer depend on each other, they can now run in parallel like Extraction does.

### 1.2 Parallelize the Teaching pass
- **Where:** `AIService`.
- **Change:** Run Teaching calls concurrently, similar to Extraction's worker pool.
- **Caution:** Use 2 workers, not 3 — Extraction's 3-worker burst already filled the TPM window and triggered a 15–60s cooldown; Teaching's per-call payload is heavier than Extraction's, so it will hit the ceiling faster at the same concurrency.

### 1.3 Minify the knowledge JSON serialization
- **Where:** Wherever `knowledge_JSON` is serialized for the Teaching prompt.
- **Change:** `json.dumps(data, separators=(",", ":"))` instead of pretty-printed/indented output.
- **Why:** Free 10–20% token reduction, zero content loss — whitespace and formatting cost tokens too.

### 1.4 Split extraction fields by which pipeline stage actually needs them
- **Change:** Keep `reasoning`, `intuition`, `why_it_matters`, `examples` in the Teaching input — these are what fixed the "explains what not why" problem, don't cut them. Move `connections` (cross-topic links) to Merge-stage input only, since cross-topic relationships are Merge's job, not any single topic's.

### 1.5 Verify current Groq per-model TPM before finalizing which model runs Teaching
- **Action:** Check `console.groq.com/docs/models` directly (lineup shifts often, with little notice).
- **Known as of last check:** `qwen/qwen3-32b` = 6K TPM (current bottleneck model). `openai/gpt-oss-120b` = 8K TPM. `llama-3.3-70b-versatile` reportedly 12K TPM if still live — verify before relying on it.
- **Also swap:** any reference to deprecated model strings (`llama-3.3-70b-versatile` may itself be deprecated — check) → fallback to `openai/gpt-oss-120b` for reasoning-heavy passes (Teaching, Merge), a faster/cheaper model for Outline/Extraction.

### 1.6 Investigate Groq prompt caching
- **Action:** Check whether the repeated `TEACHING_PROMPT` system prompt (identical every call) qualifies as a cached prefix. Groq docs state cached input tokens don't count toward TPM. If applicable, this reclaims ~1547 tokens/call for free. Verify exact invocation mechanics before assuming it's automatic.

### 1.7 Fix chunk token estimator
- **Where:** `Chunker`.
- **Change:** Replace `max(1, len(word)//4)` per-word with `len(full_chunk_text) // 4` applied once to the whole chunk.
- **Why:** Per-word estimation rounds most English words to 0–1, silently under-counting total tokens across a document.

---

## Priority 2 — Trust / groundedness (prevents silent fabrication)

### 2.1 Empty/thin-source guard clause
- **Where:** `ExtractionService` / `DocumentProcessor`.
- **Change:** If extracted text for a `KnowledgeSource` is empty or below a minimum length threshold, mark it `FAILED` and never let it reach Outline/Teaching.
- **Output on failure:** A visible "couldn't extract text from this file" placeholder in the final document — not silence, not fabrication.
- **Why:** Observed a fully hallucinated RL study guide generated from a source the model itself had already identified (in its own reasoning) as empty. An empty source must produce a visible gap, never confident-sounding invented content.

### 2.2 Coverage-aware, scoped elaboration ("fill in the blanks," done safely)
- **Where:** Extraction schema + Teaching prompt.
- **Add field:** `coverage: thin | adequate | rich` per topic, based on how much the source actually said.
- **Teaching rule:**
  - Standard, well-established domain concepts with one settled explanation → safe to elaborate even when `coverage: thin` (no real ambiguity to get wrong).
  - Anything specific to *this* source (instructor's own examples, opinions, exact numbers, a particular framing) → must stay strictly grounded in what was extracted. Do not invent specifics.
- **Mark supplemented content:** When the model adds background beyond the source, flag it distinctly, e.g. `> [!info] General background, not covered in this specific source` — don't blend it invisibly into source-grounded prose.

### 2.3 Grounding check on technical specifics
- **Where:** Teaching prompt.
- **Add instruction:** Only include specific parameters/technical details (e.g. named hyperparameters, specific library functions) that the source actually covered — do not pad with outside documentation knowledge presented as if it were part of the lecture.

---

## Priority 3 — Prompt-level content quality

### 3.1 No meta-commentary about the source's own structure
- **Where:** Teaching prompt.
- **Add instruction:** Never write sentences referencing "this section," "the following sections," "the video," or the source's own structure. Write the material itself, not commentary about the material's organization.

### 3.2 Cap analogy density
- **Where:** Teaching prompt.
- **Add instruction:** One strong analogy per major concept, not one per paragraph. Repeating the same comparison reworded is filler, not intuition.

### 3.3 No vague pseudo-intuition
- **Where:** Teaching prompt.
- **Add instruction:** If extraction captured no real analogy from the source, either produce one concrete, simple, explicit comparison, or omit the analogy line entirely. A vague abstract restatement that sounds like intuition but isn't is worse than no analogy.

### 3.4 Few-shot exemplar (if not already added)
- **Where:** Teaching prompt.
- Add 1–2 worked examples of input knowledge → good "why-first" output. This anchors depth better than instructions alone.

---

## Priority 4 — Merge pass fixes

### 4.1 Fix mid-document truncation
- **Where:** Merge call.
- **Change:** Increase `max_tokens` headroom for the merge call; verify it scales with document length. If long documents still overflow a single merge call, merge in pairs hierarchically (merge groups of 2–4 sections, then merge those results) rather than one giant final call.
- **Why:** Two separate test runs (test11, test19) both cut off mid-sentence — this is systemic, not a one-off.

### 4.2 Normalize heading hierarchy
- **Where:** Merge pass / `MarkdownRenderer`.
- **Change:** Ensure combined sections share consistent heading depth (don't concatenate sections that each assumed they were the top-level document).

### 4.3 Explicit terminology/glossary pass
- **Where:** Merge prompt.
- **Add instruction:** Enforce consistent terminology and phrasing for the same concept throughout the merged document. This now carries more of the continuity weight since 1.1 removed rolling context.

---

## Priority 5 — Formatting hygiene

### 5.1 Mermaid — prevent, then validate, don't just patch
- **Prompt constraint:** Node IDs must be plain alphanumeric; all labels double-quoted; no parentheses or nested brackets inside labels.
- **Post-generation validation gate:** Attempt a basic syntax sanity-check on generated Mermaid blocks. If it fails, strip the diagram entirely rather than ship broken syntax that crashes rendering.

### 5.2 Strip dead `mermaid.live` image links
- **Where:** Post-processing / `MarkdownRenderer`.
- **Change:** Regex-strip any `![...](https://mermaid.live/...)` pattern — the native ` ```mermaid ` code block already renders in Obsidian; the image link is dead and redundant.

### 5.3 Strip stray ` ```markdown ` code fences
- Confirm this is actually catching all cases — still appearing in some outputs despite being on the "tried" list.


---

## Hygiene (parallel, low priority, low effort)
- `tenacity` retries for 429s (partially done per earlier notes — confirm coverage).
- Trim `requirements.txt` of unused packages (jupyter, streamlit, pandas, xgboost, altair if unused).
- Write `README.md`.
- Expand test coverage past the current baseline.
