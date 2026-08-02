# Day 12 — The YouTube Wall Breaks

**Phase:** Deployment Hardening & Mobile UX

**Focus:** Finally solving YouTube extraction on the cloud (Render's datacenter IP is blocked by YouTube), making the mobile experience feel native, and fixing the Cloudflare 520 timeout that killed long generation runs on phones.

**Duration:** ~6 hours

---

# Overview

Day 11 left YouTube links broken in production: every fallback step failed on Render because the cloud server's IP is blocked by YouTube's transcript endpoint. The `youtube-transcript-api` library works locally (home IP) but not from Render's datacenter. Day 12 was the day that wall finally came down — not by getting YouTube to like our IP, but by sidestepping the fetch entirely and asking Gemini to transcribe the video on Google's servers. The rest of the day was spent hardening deployment (the Cloudflare 520 bug that only showed up on phones) and doing a final mobile polish pass on the bento cards.

---

# Round 1: The Root Cause Confirmed

**Problem:** A YouTube URL pasted on the live site produced "Could not extract transcript from this video." The full fallback chain was logging:

```
gemini: Gemini returned an empty transcript
direct: YouTube blocked this server's IP
free hosted service: Hosted service returned no usable transcript
home helper: HOME_HELPER_URL not set
```

All three real fallbacks were dead from the cloud:
- **`direct`** (`youtube-transcript-api`) — YouTube refuses the Render IP range.
- **`free hosted service`** (`youtube-transcript.ai`) — rate-limits cloud/datacenter IPs almost immediately (works fine from a home IP).
- **`home helper`** — a Tailscale tunnel back to a home PC, deliberately not configured (user wanted to avoid leaving a PC on 24/7 and paying).

The insight: every path that *downloaded the captions ourselves* was doomed, because the fetch happens from Render. The fix had to move the fetching to someone whose IP YouTube likes.

---

# Round 2: Gemini-Native Transcription (the breakthrough)

**Solution:** Gemini's `models.generate_content` accepts a YouTube URL directly as a `FileData` part. Google's own servers fetch and decode the video — our server never touches the video bytes, so the IP block is irrelevant.

**Implemented `GeminiClient.transcribe_youtube()` (`app/llm/gemini_client.py`):**
- Sends `types.Part(file_data=types.FileData(file_uri=url))` alongside the transcription prompt
- Uses `gemini-3.1-flash-lite` (the fast model, no extra cost path)
- Config: `max_output_tokens=65536`, `media_resolution=MEDIA_RESOLUTION_LOW` (keeps latency and cost down)
- Verbatim prompt first: *"Transcribe this video's full spoken content as accurately as possible, in order, as plain text."*
- On empty response, retries once with a paraphrase prompt: *"Transcribe section by section in ~2 minute sections, in your own words, keeping every detail."*
- Raises `ValueError("Gemini returned an empty transcript (finish reason: ...)")` if both attempts come back empty

**Fallback integration (`app/ingestion/extractors/youtube_extractor.py`):**
- Prepended a new first step in the fallback chain: `("gemini", _fetch_via_gemini)`
- `_fetch_via_gemini(video_id)` builds `https://www.youtube.com/watch?v=<id>` and requires ≥50 words before accepting the result
- So the new order is: `gemini` → `direct` → `free hosted service` → `home helper`

**Caveats documented (all free-tier):**
- Only PUBLIC videos (no private/unlisted)
- 8 hours of YouTube video/day cap on the free preview
- Very long videos may overflow the context window — the caller falls through to the other paths
- The recitation (copyright) filter can block lyrics/copyright-heavy videos — that's exactly what the paraphrase retry exists for

---

# Round 3: The Recitation Wall

**Problem:** During local verification, the paraphrase retry path got its first real workout. Test video `pYxNSUDSFH4` came back empty from the verbatim prompt — Gemini's recitation filter refused to reproduce the speech verbatim.

**Verification results:**
| Video | Verbatim | Paraphrase retry |
|---|---|---|
| `gg7WjuFs8F4` (AlphaFold lecture) | ✅ ~1,330 words | n/a |
| `pYxNSUDSFH4` | ❌ RECITATION-blocked | ✅ 593 words (~96% fidelity) |

The paraphrase prompt passed where verbatim failed because rephrasing in "your own words" dodges the copyright-detection trigger while keeping the content. The `finish_reason` is surfaced in the error message when both attempts fail, so diagnostics show *why*.

---

# Round 4: Live Test — "IT WORKED!"

**Deploy & verify:** Both commits pushed, Render auto-deployed, and the first real URL test on the live site succeeded — the first successful YouTube extraction from the cloud in the project's history. The `Detail:` log line now shows:

```
gemini: <transcript fetched> | direct: (skipped) | ...
```

Follow-up testing on the phone exposed the 520 bug (Round 5), but extraction itself was solved.

---

# Round 5: The Cloudflare 520 (only on phones)

**Symptom:** A phone request running a YouTube link would fail "after some time" with a Cloudflare error page:

```
520: Web server is returning an unknown error. (Ray ID: a24d40cd3efa550b)
```

**Diagnosis from the Render logs:** The phone's `POST /process` logged `200` with only **1,808 bytes** — but the merged markdown alone is ~19,500 chars. So the stream died after the first few progress lines while the server kept working. A `==> Detected service running on port 10000` Render boot banner was interleaved mid-request, and Cloudflare relayed a truncated/empty response → 520.

**Two independent causes, both fixed:**

1. **Gunicorn worker timeout** — `Procfile` had `--timeout 300` (5 min). A YouTube run easily exceeds that: Gemini video transcription is one blocking call with no yields, plus Groq's `Waiting 60s` TPM backoffs, plus a blocking merge and quality-gate.
   - **Fix:** `--timeout 300` → `--timeout 900`.

2. **Long silent steps** — `extraction`, `generate_outline`, `merge_sections`, and `quality_gate.run` all run with **zero bytes flowing** to the client. Cloudflare's proxy idle limit is ~100s, so any step quiet that long gets cut → 520 "after some time."
   - **Fix:** Added `PipelineService._heartbeat()` (`app/services/pipeline_service.py`) — a background thread runs the blocking step while the generator yields a `"Still working..."` status line every 15s. Applied to all 4 silent steps via `yield from self._heartbeat(...)`.
   - The heartbeat reuses the **current step's pct** (not a low fixed value), because the frontend sets the progress bar width directly — a stale low pct would make it jump backward.
   - Matches the existing `sub_gen` generator pattern already used in the pipeline.

**Result:** the progress bar now keeps moving during long LLM calls, and neither gunicorn nor Cloudflare can drop the connection mid-generation.

---

# Round 6: Mobile Responsiveness Pass

**Context:** The user confirmed "everything works, frontend wise" but wanted the mobile experience cleaned up. Several fixes across `index.html` and `about.html`:

- **Hamburger menu** — smooth staggered dropdown (cubic-bezier `0.22,1,0.36,1`), links cascade in at 0.08s/0.14s/0.2s, theme toggle at 0.26s. Applied to both pages.
- **Hero visual** — on mobile the note-card and chips now stack vertically (`flex-wrap`) instead of overlapping absolutely; `--rot:0deg` so the float animation doesn't tilt them.
- **About pipeline** — turns vertical on ≤640px (`flex-direction:column`, vertical pipe line, `pipeTravelV` animation).
- **Dividers & CTAs** — `.divider-text` wraps on mobile, CTA bands get tighter padding, `.btn-primary` prevents wrapping.
- **New FAQ item** — "What are the limitations of YouTube links?" (recommends a `.txt`/exported transcript for multi-hour lectures, since free-tier constraints block very long direct links).

---

# Round 7: Bento Card Polish (the last 1%)

The user's final pass was on the "Why it's different" bento cards (01–05). Three rounds of tightening:

1. **Icon overlap (card 01):** On mobile the big card's long description overflowed its single 150px grid row, so the absolutely-positioned icon overlapped the title and text. Fix: big card spans 2 rows on small screens.

2. **Inconsistent icon-to-title spacing:** The icon was absolutely positioned at the top while text was pinned to the card bottom (`justify-content:flex-end`), so the gap varied wildly by card height — huge on the tall card 01. Fix: icon moved into normal flow (`margin-bottom:18px`) above the title for **all five cards**, and grid rows changed to `minmax(150px, auto)` so nothing clips.

3. **Card 01 still too tall:** It spanned 2 grid rows, leaving empty space under the description. Fix: single-row span on all breakpoints, desktop grid reflowed 4→3 columns (big card takes 2) so the layout has no holes. Card 01 now hugs its content exactly like cards 02–05.

---

# Files Modified Today

| File | Changes |
|------|---------|
| `app/llm/gemini_client.py` | New `transcribe_youtube()` — YouTube URL as `FileData` part, verbatim→paraphrase retry, `max_output_tokens=65536`, `MEDIA_RESOLUTION_LOW` |
| `app/ingestion/extractors/youtube_extractor.py` | New `_fetch_via_gemini()` prepended as first fallback step (`("gemini", ...)`) |
| `Procfile` | gunicorn `--timeout 300` → `--timeout 900` |
| `app/services/pipeline_service.py` | Added `_heartbeat()` helper (thread + yield); wrapped extraction, outline, merge, quality-gate |
| `app/templates/index.html` | Hamburger stagger, hero-visual mobile stacking, divider/CTA mobile CSS, YouTube-limitations FAQ item, bento card fixes (overlap, spacing, size) |
| `app/templates/about.html` | Hamburger stagger, vertical pipeline on ≤640px, divider/CTA mobile fixes |
| `development log/Log 12.md` | This file |

---

# Current State (End of Day 12)

**Working:**
- ✅ YouTube links extract on Render (first time ever) via Gemini-native transcription
- ✅ Recitation-blocked videos recovered via paraphrase retry (~96% fidelity)
- ✅ Fallback chain order: gemini → direct → hosted → home helper
- ✅ Cloudflare 520 gone — gunicorn timeout raised + 15s heartbeats on all silent steps
- ✅ Progress bar keeps moving during long LLM calls on phones
- ✅ Hamburger menu animations on both pages
- ✅ Hero visual stacks cleanly on mobile
- ✅ About pipeline vertical on small screens
- ✅ Bento cards 01–05: no icon overlap, uniform 18px icon→title gap, content-hugging heights

**Known limits (free-tier, documented in FAQ):**
- ⚠️ Public videos only; 8h/day preview cap; very long videos fall through to other paths
- ⚠️ Render free-tier instance restarts mid-request can't be prevented in code — a 520 there would be infra, not the app

---

# Key Decisions Made Today

1. **Move the fetch, don't fight the block.** Every caption-download approach died because the download happened from Render's IP. Gemini accepts the URL and does the fetching on Google's servers — the cleanest possible bypass with zero extra infrastructure.

2. **Paraphrase retry over verbatim-only.** The recitation filter is content-dependent; a second attempt in "your own words" recovers the ~96% case at the cost of one extra call. Failure surfaces `finish_reason` so the next fallback knows why.

3. **Heartbeats in the pipeline, not the route.** The silent steps live in `PipelineService`, so that's where the keep-alive belongs — consistent with the existing `sub_gen` pattern. The route and frontend needed zero changes.

4. **Reuse current pct for heartbeats.** The frontend writes `data.pct` straight to the progress-bar width. A heartbeat at a low fixed pct would visibly regress the bar; echoing the step's own pct is invisible.

5. **Uniform icon spacing over "design accent".** The big-card icon floating far from its title looked intentional but read as broken. Normal-flow icon + one margin rule for all five cards is simpler and visually consistent.

---

# Next Session Start Points

1. **Long-video stress test** — verify Gemini transcription + heartbeats hold up on a 1–3 hour lecture from the cloud (context-window overflow is still a real ceiling).
2. **Confirm 8h/day cap behavior** — what exactly happens at the free-preview limit, and whether the fallback chain handles it gracefully.
3. **Home helper** — still unconfigured; if free-tier limits become the bottleneck, it's the only remaining fallback to wire up.
4. **Verify no stray `**` formatting** in final markdown from the merged transitions (QA regression pass on a multi-source run).

---

# Lessons Learned

1. **A block isn't always a wall — sometimes it's a detour sign.** Render's IP is blocked by YouTube; the answer wasn't better fetching, it was *not fetching*. Offloading the fetch to a service whose IP is trusted (Gemini) turned a hard block into a non-issue.

2. **Phone tests find bugs desktop tests can't.** The 520 only appeared from mobile because it was a timing/idle-timeout issue — the desktop test happened to finish faster. Test on the slowest client you have.

3. **Streaming requires the server to *keep talking*.** A generator that's "working" is invisible to a proxy if it isn't emitting bytes. Gunicorn and Cloudflare both measure silence, not progress — heartbeats are the bridge.

4. **Spacing bugs are the last 1% but the most visible.** Three separate rounds on the bento cards: overlap, then inconsistent gap, then residual height. Small CSS details dominate the final user impression of "finished."
