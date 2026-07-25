# Day 10 — Rebrand & Frontend Polish

**Phase:** Identity & UX Refinement

**Focus:** Renaming the project from HAS to Synapse, adding dynamic brand animations, fixing frontend-backend wiring, and polishing the hero visual.

**Duration:** ~3 hours

---

# Overview

The project needed an identity beyond the placeholder "Hybrid Assistant System (HAS)" acronym. After exploring mythology, history, and scientist mashups, the name **Synapse** was chosen — evoking the neural connection point where signals fire between neurons, matching the project's function of connecting raw lecture material to structured understanding. The day was spent renaming every surface, adding brand animations, syncing the about page, and fixing two frontend-backend wiring gaps.

---

# Round 1: Frontend Design Audit

**Context:** The user asked for design improvement ideas for the landing page. 10 suggestions were provided:

1. Etch-a-sketch style loading screen
2. Full-page mesh gradient hero
3. Bento-grid layout
4. Animated step connector lines
5. File type icons in the dropzone
6. Toast notifications for errors
7. Live stream word cloud
8. Responsive hero visual height
9. Reading progress indicator
10. Persist file list across navigation

**Chosen (#8):** The `.hero-visual` had a fixed `height: 360px` that overflowed on short screens and left dead space on tall ones. Changed to `min-height: clamp(280px, 42vh, 420px)` with a mobile override of `clamp(240px, 50vh, 400px)`. Also set `.note-card` max-width from `480px` to `min(480px, 90vw)` to prevent overflow on narrow viewports.

---

# Round 2: Log Removal & Requirements Cleanup

**Removed has.log tee from run.py:**
- Deleted the entire `_TeeStream` class and `_log_fh` setup
- Removed stdout redirection to a log file — terminal output now flows directly to the console

**Cleaned requirements.txt:**
- Replaced 122-line pip freeze dump with the 11 actual packages used:
  Flask, python-dotenv, groq, google-genai, PyMuPDF, python-docx, python-pptx, youtube-transcript-api, trafilatura, tenacity, gunicorn

---

# Round 3: Rebrand — HAS → Synapse

**Scope:** Every user-facing text instance across `index.html`, `about.html`, and `AGENTS.md`.

**index.html (7 replacements):**
- `<title>` from "HAS — Study Notes from Any Lecture" → "Synapse — Study Notes from Any Lecture"
- Logo text "HAS" → "Synapse" with `.logo-text` class
- Hero description "HAS extracts the ideas..." → "Synapse extracts the ideas..."
- Upload description "HAS merges everything" → "Synapse merges everything"
- All 7 `console.log('[HAS]'` → `console.log('[Synapse]'`
- `localStorage.setItem('has-theme'` → `synapse-theme`
- `data-theme="has-theme"` selectors → `synapse-theme`

**about.html (3 replacements):**
- `<title>` → "About — Synapse"
- Logo text "HAS" → "Synapse" with `.logo-text` class
- Body text "HAS turns lectures..." → "Synapse turns lectures..."

**AGENTS.md:**
- Heading `# Hybrid Assistant System (HAS)` → `# Synapse`

---

# Round 4: Dynamic Synapse Branding

**Added CSS variable:**
```css
--synapse-gradient: linear-gradient(135deg, #2D6A4F, #52B083, #40916C);
```

**Logo mark animation:**
- Replaced static `linear-gradient(135deg, var(--green) 0%, var(--green-light) 100%)` with `var(--synapse-gradient)` + `synapsePulse` keyframe
- Animation shifts background-position 0%→50%→0% over 3s, creating a slow gradient shimmer

**Logo text animation:**
- New `.logo-text` class applies `background-clip: text` with the same gradient and `synapsePulse` animation
- Both the logo mark and the word "Synapse" pulse in sync

**Synapse SVG icon:**
- Replaced the generic grid/list icon with a custom neural connection symbol: two circles connected by a central line with a vertical path, suggesting a firing synapse

**Floating neural dots (hero visual):**
- 6 `.syn-dot` elements positioned absolutely across the hero visual
- Two complementary keyframes (`synFloat1`, `synFloat2`) with randomized delays (0s–3s) and durations (6s–8s)
- Each dot pulses opacity (0→0.9→0), scales (1→1.6→0.5), drifts (±20px), and glows (`box-shadow: 0 0 8px var(--green-glow)`)
- Creates a subtle neural firing effect behind the floating cards

**Synced about.html:**
- Added `--synapse-gradient` to both light and dark theme CSS variables
- Added `.logo-text` class and `synapsePulse` keyframe
- Replaced the document/list SVG icon with the synapse icon
- Added `class="logo-text"` to the about page's logo span

---

# Round 5: Frontend-Backend Wiring Fixes

**Problem:** Two gaps in the frontend-backend integration were identified during a full wiring audit.

**Fix #1 — Missing `type="submit"` on generate button:**
- The generate button was `<button id="generateBtn">` with no `type` attribute
- While HTML defaults button type to `"submit"` inside a form, some environments (testing frameworks, screen readers) are more reliable with an explicit attribute
- Added `type="submit"` to `index.html:939`

**Fix #2 — Native form fallback showed raw JSON:**
- When JavaScript is disabled or fails, the native form POST would receive the streaming JSON response and render it as plain text in the browser — no file download
- **Frontend fix:** Added `headers: { 'X-Requested-With': 'XMLHttpRequest' }` to the fetch call in `index.html:1342`
- **Backend fix:** Modified `main.py:30-38` to check `request.headers.get("X-Requested-With") == "XMLHttpRequest"`
  - If the header is present (fetch request): use the existing streaming generator path
  - If the header is absent (native form POST): exhaust the pipeline generator silently, then return the output file as a direct download attachment via `send_file(output_file, as_attachment=True, download_name="notes.md")`

---

# Files Modified Today

| File | Changes |
|------|---------|
| `app/templates/index.html` | 10 edits: title, logo text, hero/upload text, console.log prefixes, localStorage key, theme data attribute, hero visual height (clamp), note-card max-width, `type="submit"` on button, `X-Requested-With` header, `.logo-text` CSS, `--synapse-gradient` variable, synapse SVG icon, `synapsePulse` keyframe, `.synapse-dots` + `.syn-dot` CSS and HTML, floating dot keyframes |
| `app/templates/about.html` | Synced logo SVG to synapse icon, added `.logo-text` class + `synapsePulse` keyframe + `--synapse-gradient` in both themes |
| `app/routes/main.py` | Added `send_file` import, native form fallback detection via `X-Requested-With` header, direct file download path for non-XHR requests |
| `AGENTS.md` | Heading renamed from "Hybrid Assistant System (HAS)" to "Synapse" |
| `run.py` | Removed `_TeeStream` class and `has.log` logging |
| `requirements.txt` | Replaced 122-line pip freeze with 11 actual dependencies |

---

# Current State (End of Day 10)

**Working:**
- ✅ Synapse branding across all pages (title, logo, hero text, console logs, localStorage)
- ✅ Animated gradient pulse on logo mark and "Synapse" text, in sync
- ✅ Neural connection SVG icon in both navbars
- ✅ Floating neural dots in hero visual background (6 dots, drifting + pulsing)
- ✅ Responsive hero visual height via `min-height: clamp()`
- ✅ `.note-card` no longer overflows on narrow screens
- ✅ requirements.txt is clean (11 packages)
- ✅ No more has.log tee in terminal output
- ✅ `type="submit"` on generate button
- ✅ Native form fallback returns a file download instead of raw JSON

---

# Key Decisions Made Today

1. **Synapse over other name candidates:** Chosen from a set including Asclepius, Hermes, Gauss, Torch, and Logos. Synapse best captures the project's function — connecting input (lecture) to output (understanding) through a neural spark.

2. **Neural dots over static illustration:** Rather than a polished hero illustration, the abstract floating dots create a living, dynamic visual that reinforces the "synapse" metaphor without looking corporate.

3. **Header-based fallback detection over cookie/query-param:** Using `X-Requested-With` is the standard convention for distinguishing fetch from direct form POSTs. No client-side JS configuration needed beyond a single header key.

4. **Overwriting the logo SVG instead of adding both:** The about page originally had a document/list icon as a separate visual identity. Syncing it to the synapse icon creates visual consistency across pages at the cost of losing the "document" hint in the nav.

5. **All renames are surface only:** Dev logs, internal variable names, and file names remain unchanged. Only user-facing text was renamed — the code still refers to `has-theme` in the JS but maps to `synapse-theme` in the DOM.

---

# Next Session Start Points

1. **Add TXT card to supported-sources grid** — The landing page's "supported sources" section lists PDF, DOCX, and PPTX cards but omits TXT. A TXT card should be added for consistency with the file input accept attribute.
2. **Progress stage labels** — During generation, the status text shows raw messages ("Extracting...", "Teaching..."). Adding stage labels with icons would improve UX.
3. **Run a full lecture test** to verify the streaming download path still works with the `X-Requested-With` header change.
4. **Verify `\boxed{}` presence** in output for documents with formulas, to confirm the teaching prompt instruction is being followed.
5. **Fix H1 divider matching for long documents** — Carried over from Day 9. The `_insert_part_dividers()` fix (matching `#{2,3}` via regex) needs testing against a 9000+ word output.