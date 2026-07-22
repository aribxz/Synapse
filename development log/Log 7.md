# Day 7 — Frontend Overhaul & UI Wiring

**Phase:** Frontend Design & Backend Integration

**Focus:** Replacing the bare-bones test form with a premium, production-quality landing page, then wiring it to the Flask backend.

---

# Overview

Day 6 ended with a working pipeline (test26.md) that produced clean study notes with diagrams, callouts, and wiki-links. The pipeline was solid. But the user interface was a 32-line HTML form with no styling — fine for development, unusable for anyone else.

Today we replaced it entirely. The user had a reference video showing a premium minimalist editorial design (cream background, Anthropic-style font, green accents, smooth animations). I wrote a detailed prompt for Claude to generate the frontend, then spent the rest of the day wiring it to the backend and debugging why nothing worked.

---

# The New Frontend

The user wanted something that looked like a Linear, Framer, or Apple landing page — but warm and cream-toned instead of dark mode.

**Design Reference (from the video description):**
- Background: smooth solid cream `#F4EBDD`
- White card elements with generous whitespace and 12-20px rounded corners
- Clean geometric sans-serif (Inter, similar to Anthropic's font)
- Bold near-black `#1A1A1A` headings, soft gray `#6B6B6B` body text
- Green accent `#2D6A4F` / `#40916C` buttons
- Low-opacity drop shadows, thin gray dividers, minimal icons

**I wrote a Claude prompt** describing the project (HAS — Hybrid Assistant System), the design aesthetic, and exactly what sections the landing page needed:
- Hero with animated floating note-card mockup
- How It Works (4-step pipeline cards)
- Supported Sources grid (YouTube, PDF, DOCX, PPTX, Webpage)
- Upload section with drag-and-drop file zone + URL textarea
- Output preview (dark code-block card)
- Stats band with animated counters
- Minimal footer

**Animations:** Body fade-in, scroll-triggered reveal (IntersectionObserver), floating cards (CSS keyframes), shimmer progress bar, button hover lifts, typing cursor in hero.

---

# The CSS Semicolon Bug

When the user dropped the new HTML into templates and ran the server, all they saw was a cream-colored page. The body was at `opacity: 0` because of a missing semicolon:

```css
--ease: cubic-bezier(0.22, 1, 0.36, 1)    /* ← no semicolon */
--ease-soft: cubic-bezier(0.4, 0, 0.2, 1);
```

Without the semicolon, the CSS parser treated `--ease-soft: ...` as part of `--ease`'s value, invalidating both custom properties. The body animation `bodyFadeIn 0.9s var(--ease) forwards` silently failed because `var(--ease)` was invalid, so the body stayed at `opacity: 0`. The cream background bled through but all content was invisible.

**Fix:** One semicolon.

---

# Frontend to Backend Wiring

The new HTML had no `<form>` element — just a `<button>` with a `click` event handler that used `fetch()` to POST FormData to `/process`. The original 32-line template used a native form post, so this was a complete rewrite of how the frontend communicates with the backend.

## Problem 1: No Native Fallback

The entire submission relied on JavaScript. If the JS failed to load (syntax error, network issue, browser extension), the button did nothing. No server request, no download, just silence.

**Fix:** Wrapped the upload section in a `<form>` with `action="/process" method="POST" enctype="multipart/form-data"`. Added `name="files"` to the file input and `name="urls"` to the textarea. This gives a native form submit as fallback if JavaScript doesn't load.

## Problem 2: Wrong Event

The original JS was:
```javascript
generateBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    // ... fetch logic
});
```

Inside a `<form>`, clicking a `<button>` (default type="submit") triggers the form's `submit` event, not the button's `click` event. `e.preventDefault()` on a `click` event does NOT prevent form submission — you need to cancel the `submit` event. So the button triggered BOTH the JS fetch AND a native form submission, causing a race condition.

**Fix:** Changed to form submit event:
```javascript
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    // ... fetch logic
});
```

Now `e.preventDefault()` on the `submit` event correctly stops native form submission. The JS fetch runs clean. If JS fails entirely, the native submit is the fallback.

## Problem 3: Button Visual Feedback

The user couldn't open DevTools (F12 didn't work on their hardware) so they had no way to see if the JS was running or throwing errors. All console.log calls were invisible.

**Fix:** Added a visible flash on the button when the submit handler fires:
```javascript
generateBtn.style.transform = 'scale(0.97)';
setTimeout(() => generateBtn.style.transform = '', 150);
```

The button briefly shrinks on click, confirming the handler fired. No DevTools needed.

---

# The Terminal Printing Nightmare

The user repeatedly said "nothing is printing in the terminal." The pipeline worked (files generated), but all `print()` statements — pipeline logs, outline output, model status — were invisible.

## Attempt 1: flush=True

Added `flush=True` to every `print()` call in pipeline_service.py, main.py, client.py, gemini_client.py, chunker.py, and quality_gate.py. Didn't help.

## Attempt 2: PYTHONUNBUFFERED

Set `$env:PYTHONUNBUFFERED = "1"` but Flask's debug mode reloader spawns a child process that doesn't inherit the setting on Windows. Didn't help.

## Attempt 3: use_reloader=False

Disabled the reloader so Flask runs in the main process. No more child process to swallow stdout. Still didn't help.

## Attempt 4: builtins.print Monkeypatch

```python
import builtins
builtins.print = functools.partial(print, flush=True)
```

Only patches `run.py`'s scope — other modules still use the unpatched built-in. Also fragile when modules import `print` during their own import chain. Didn't help.

## Attempt 5: sys.stdout Wrapper (Final)

```python
class _TeeStream:
    def __init__(self, original):
        self.original = original
    def write(self, data):
        self.original.write(data)
        self.original.flush()
        _log_fh.write(data)
        _log_fh.flush()

sys.stdout = _TeeStream(sys.stdout)
sys.stderr = _TeeStream(sys.stderr)
```

Every stdout write — from any module, any library, Flask itself — goes through this wrapper. Flushed immediately and teed to `has.log`. The log file confirmed Flask does start and the pipeline does run. But even with stdout wrapped, the terminal was silent.

**Root cause (likely):** Windows PowerShell handles stdout from Python processes differently, especially with Flask's threaded request handling. The wrapper writes and flushes, but PowerShell might not display it in real-time. The `has.log` file has all the output — the terminal just doesn't show it.

**Result:** All output goes to both terminal and `has.log`. Terminal is still unreliable on Windows, but `has.log` captures everything.

---

# Current State

**Working:**
- ✅ Premium frontend renders with cream bg, Inter font, green accents
- ✅ Form submit handler sends POST to /process with FormData
- ✅ Native form submit fallback if JS is disabled
- ✅ Button flashes on click for visual feedback
- ✅ Pipeline runs end-to-end (generates `app/outputs/notes.md`)
- ✅ All `print()` output teed to `has.log`

**Broken:**
- ❌ Terminal printing still unreliable on Windows (stdout wrapper flushes but PowerShell doesn't always display it)
- ❌ API limits exhausted (output quality degraded — "breached our limits")

---

# Files Modified Today

| File | Changes |
|------|---------|
| `app/templates/index.html` | Complete replacement: 1,172 lines of premium UI (was 32). Added form wrapper, name attributes, submit event handler, button flash, console.log debugging |
| `run.py` | Sys.stdout/stderr wrapper with `_TeeStream`, flush + file tee, `use_reloader=False` |
| `app/routes/main.py` | Added flush=True to pipeline start/finish prints |
| `app/services/pipeline_service.py` | Added flush=True to all prints |
| `app/llm/client.py` | Added flush=True to model/gen prints |
| `app/llm/gemini_client.py` | Added flush=True to model/gen prints |
| `app/chunking/chunker.py` | Added flush=True to chunk prints |
| `app/services/quality_gate.py` | Added flush=True to `_safe_print()` |
| `AGENTS.md` | Rewritten with concise project summary for next session |

---

# Lessons Learned

1. **A missing semicolon can make an entire page invisible.** CSS custom property chains fail silently — the browser doesn't warn.

2. **Button click does not prevent form submission.** Inside a `<form>`, `e.preventDefault()` on the `click` event is useless. Always listen to the `submit` event on the form element.

3. **builtins.print monkeypatching is fragile.** It only affects the module where it's defined. Modules imported after the patch use the patched version, but any module that captured the original `print` during its own import stays with the old version. A `sys.stdout` wrapper is more reliable because every `print()` ultimately calls `sys.stdout.write()`.

4. **Flask's reloader on Windows swallows stdout.** The child process inherits the console handle but stdout buffering behavior differs from the parent. `use_reloader=False` helps but doesn't fully solve it.

5. **File tee is more reliable than terminal output on Windows.** When debugging, write to a file. The file system doesn't have the buffering quirks that PowerShell does.

6. **Always have a native form fallback.** If your entire UX depends on JavaScript working, you're one ad blocker or browser extension away from a broken app. Progressive enhancement still matters.
