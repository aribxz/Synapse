import json
import re
import time
import math
import threading

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pprint import pprint
from app.llm.client import GroqClient
from app.llm.gemini_client import GeminiClient
from app.llm.prompt_builder import PromptBuilder
from app.llm.outline_parser import OutlineParser
from app.llm.extraction_parser import ExtractionParser
from app.llm.models import LLMRequest
from app.llm.prompts.repair import REPAIR_PROMPT
from app.processing.token_estimator import TokenEstimator
from config import Config


GROQ_TPM_LIMITS = {
    "llama-3.3-70b-versatile": 12000,
    "openai/gpt-oss-120b": 8000,
}

LLAMA_MODEL = "llama-3.3-70b-versatile"  # per-model on Groq on_demand tier


class AIService:
    def __init__(self):
        self._groq = GroqClient()
        self._gemini = GeminiClient()

        self.prompt_builder = PromptBuilder()
        self._groq_tpm_windows: dict[str, list] = {}
        self._groq_tpm_lock = threading.Lock()
        self._fallback_msgs: list[str] = []
        self._fallback_msgs_lock = threading.Lock()

    def _generate_fast(self, request, fast_model="gemini"): # Sends the request to the correct API provider (groq or gemini).
        if fast_model == "gemini":
            return self._gemini.generate(request, model=Config.GEMINI_FAST_MODEL)
        
        return self._groq.generate(request, model=LLAMA_MODEL)

    def _tpm_key(self, model: str) -> str: # Stores what model we are using.
        return GROQ_TPM_LIMITS.get(model, "default") 

    def _wait_for_groq_tpm(self, estimated_tokens: int = 1000, model: str = ""):
        tpm_limit = GROQ_TPM_LIMITS.get(model, 8000) # If the model isnt listed, the default is 8000.
        key = self._tpm_key(model) # model being used.

        with self._groq_tpm_lock: # Only one allowed, rest wait in the queue.
            now = time.time() # current time.
            window = self._groq_tpm_windows.setdefault(key, []) # Each api call stores time and tokens usage.
            self._groq_tpm_windows[key] = [(ts, t) for ts, t in window if now - ts < 60] # Sliding window, removes requests older than 60s.
            total_in_window = sum(t for _, t in self._groq_tpm_windows[key]) # add up the remaining tokens.

            if total_in_window + estimated_tokens > tpm_limit * 0.9: # 90% as a safety margin.
                sleep_for = max(5, 60 - (now - self._groq_tpm_windows[key][0][0])) if self._groq_tpm_windows[key] else 5 # Subtract the oldest request by 60 and wait that many seconds so that it disappears.
                print(f"  Groq TPM limit ({tpm_limit}) for {model}. Waiting {sleep_for:.0f}s...")
                time.sleep(sleep_for) # Waits.
                self._groq_tpm_windows[key] = [] # All the calls are cleared.

    def _track_groq_usage(self, usage: dict | None, model: str = ""): # API calls return a json that has a dict called usage.
        if usage and "total_tokens" in usage: # Checks if usage exists and total tokens are in it.
            key = self._tpm_key(model) # Again the current model.

            with self._groq_tpm_lock:
                window = self._groq_tpm_windows.setdefault(key, []) # Gets the token records for the current API call.
                window.append((time.time(), usage["total_tokens"])) # Adds time to those tokens and this is what we use in _wait_for_groq_tpm.

    def _run_extraction(self, topic_index: int, topic, chunks, fast_model="gemini"):
        source_text = self._collect_topic_text(topic, chunks) # Giving relevant sections to the LLMs.
        extraction_request = self.prompt_builder.build_extraction(source_text) # Builds the prompts needed.
        est = (len(extraction_request.system_prompt) + len(extraction_request.user_prompt)) // 3 + 2048 # Safety check with 2048.

        if fast_model != "gemini":
            self._wait_for_groq_tpm(est, model=LLAMA_MODEL) 

        raw_response = self._generate_fast(extraction_request, fast_model=fast_model) # Makes the actual API call. Notice how fast_model is so flexible, I am a genius.

        if fast_model != "gemini":
            self._track_groq_usage(raw_response.usage, model=LLAMA_MODEL)

        knowledge = ExtractionParser().parse(raw_response.raw_output)
        return topic_index, topic, knowledge, source_text

    def _print_extraction(self, topic_index, topic, knowledge, source_text):
        """Print extracted knowledge debug info."""
        print("\n================ EXTRACTED KNOWLEDGE ================\n")
        print("\n" + "=" * 70)
        print("TOPIC:")
        print(topic.title)
        print("\nEXAMPLES:")
        pprint(knowledge.examples)
        print("\nINTUITION:")
        pprint(knowledge.intuition)
        print("\nREASONING:")
        pprint(knowledge.reasoning)
        print("\nWHY IT MATTERS:")
        pprint(knowledge.why_it_matters)
        print(f"Source Chunks: {topic.source_chunks}")
        print(f"Characters: {len(source_text)}")
        print("=" * 70)
        print("\n====================================================\n")

    def _run_teaching(self, topic_index: int, topic, outline, knowledge, total_topics):
        req = self.prompt_builder.build_teaching(
            knowledge=knowledge,
            outline=outline,
            current_topic=topic,
            topic_index=topic_index,
            total_topics=total_topics,
        )

        kd = {k: v for k, v in asdict(knowledge).items() if k != "connections"} # Remove connections because of prompt limit.
        knowledge_size = len(json.dumps(kd, separators=(",", ":"))) # Make a json without the extra spaces.
        req.max_tokens = min(4096, max(1500, 1500 + knowledge_size // 8)) # The topic never exceeds 4096; a safety measure yet again.
        est = (len(req.system_prompt) + len(req.user_prompt)) // 3 + req.max_tokens # Estimate max tokens.

        model_used = Config.REASONING_MODEL # Once again, this is very flexible.
        self._wait_for_groq_tpm(est, model=Config.REASONING_MODEL)

        try:
            response = self._groq.generate(req, model=Config.REASONING_MODEL)
            self._track_groq_usage(response.usage, model=Config.REASONING_MODEL)
            print(f"  Topic {topic_index} ({topic.title}): served by {model_used}", flush=True)
            return topic_index, response.raw_output
        
        except Exception as e:
            if "413" not in str(e) and "rate_limit_exceeded" not in str(e): # API errors or internet issues.
                raise

            msg = f"OSS-120B rate limit hit for '{topic.title}', switching to Llama 3.3 70B"
            print(f"  {msg}", flush=True)

            with self._fallback_msgs_lock:
                self._fallback_msgs.append(msg)

        model_used = LLAMA_MODEL # Switch to llama.
        self._wait_for_groq_tpm(est, model=LLAMA_MODEL)

        try:
            response = self._groq.generate(req, model=LLAMA_MODEL)
            self._track_groq_usage(response.usage, model=LLAMA_MODEL)
            print(f"  Topic {topic_index} ({topic.title}): served by {model_used}", flush=True)
            return topic_index, response.raw_output
        
        except Exception as e:
            if "rate_limit_exceeded" not in str(e):
                raise

            msg = f"Llama 3.3 70B rate limit hit for '{topic.title}', switching to Gemini"
            print(f"  {msg}", flush=True)
            with self._fallback_msgs_lock:
                self._fallback_msgs.append(msg)

        model_used = Config.GEMINI_FAST_MODEL # If even llama fails then switch to Gemini.
        response = self._gemini.generate(req, model=Config.GEMINI_FAST_MODEL)
        print(f"  Topic {topic_index} ({topic.title}): served by {model_used}", flush=True)

        return topic_index, response.raw_output

    def generate_from_chunks(self, chunks, outline, fast_model="gemini"):
        total_topics = len(outline)

        print(f"\n--- Running {len(outline)} extractions in parallel (fast model: {fast_model}) ---")
        extraction_results: list = [None] * len(outline) # Creates an empty list of size of outline.

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_map = { # This is like handling your worker a reciept like hey work on this and when you want it later, you just ask for it.
                executor.submit(self._run_extraction, idx, topic, chunks, fast_model): idx
                for idx, topic in enumerate(outline)
            }

            completed = 0

            for future in as_completed(future_map): # This takes any the fatest completed topic, doesnt wait for chronological order.
                idx = future_map[future] # Gets the idx (why we stored it to begin with).

                try:
                    _, topic, knowledge, source_text = future.result() # We dont need the index so _
                    extraction_results[idx] = (topic, knowledge, source_text) # Store the result at the specific index in extracted_result.
                    self._print_extraction(idx, topic, knowledge, source_text)

                except Exception as e:
                    print(f"Extraction failed for topic {idx} ({outline[idx].title}): {e}")
                    extraction_results[idx] = None

                completed += 1
                yield "progress", f"Extracting: {outline[idx].title}", outline[idx].title, (completed / total_topics) * 40 # Generator for the frontend so we can feed it loading info.


        print(f"\n--- Running {len(outline)} teaching calls in parallel (2 workers) ---")

        teaching_results: list = [None] * len(outline)
        valid_count = sum(1 for r in extraction_results if r is not None) # Sums for only the topics that were processed successfully.

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_map = {}

            for idx, result in enumerate(extraction_results): # iterate through the extracted results.
                if result is None:
                    print(f"Skipping teaching for topic {idx}: extraction failed")
                    continue

                topic, knowledge, _ = result
                future = executor.submit( # Make the Teaching future for one topic.
                    self._run_teaching, idx, topic, outline, knowledge, total_topics
                )
                future_map[future] = idx # Put it at the desginated index.

            completed = 0 # reset to 0

            for future in as_completed(future_map): # once again whoever completes first.
                idx = future_map[future] # stores index.

                try:
                    _, output = future.result()
                    teaching_results[idx] = output

                except Exception as e:
                    print(f"Teaching failed for topic {idx} ({outline[idx].title}): {e}")
                    teaching_results[idx] = None

                completed += 1
                if valid_count > 0:
                    yield "progress", f"Teaching: {outline[idx].title}", outline[idx].title, 40 + (completed / valid_count) * 60

        with self._fallback_msgs_lock:
            fallbacks = list(self._fallback_msgs)
            self._fallback_msgs.clear()
        for fb in fallbacks:
            yield "progress", fb, "", 99

        outputs = []
        connections_list = [] # One final pass/overview so we can create the index in the markdown.

        for idx, result in enumerate(extraction_results):
            if result is not None and teaching_results[idx] is not None:
                tw = len(teaching_results[idx].split())
                print(f"  Topic {idx} ({outline[idx].title}): {len(teaching_results[idx])} chars / {tw} words", flush=True)
                outputs.append(teaching_results[idx])
                _, knowledge, _ = result

                if knowledge.connections:
                    connections_list.extend(knowledge.connections)

        return outputs, connections_list

    def generate_outline(self, chunks, fast_model="gemini"): # This is more of management of outline generation.
        total = len(chunks)

        if total <= 20:
            return self._generate_outline_segment(chunks, fast_model)
        
        num_segments = min(5, max(2, (total + 10) // 20)) # Number of outlines; max of 5 ensures balance.
        seg_size = math.ceil(total / num_segments) # How many chunks will be in each outline segment.

        all_topics = []
        offset = 0 # Kind of acts as translation between previous chunks and the incomings.

        for i in range(0, total, seg_size): # Loops through individual segments of chunks.
            segment = chunks[i:i + seg_size] # slices; ex: 1 to 18 then 18 to 39 etc.
            seg_topics = self._generate_outline_segment(segment, fast_model)

            for t in seg_topics:
                t.source_chunks = [c + offset for c in t.source_chunks] # Using offset you arrange the chunk numbers according to what they were originally.

            all_topics.extend(seg_topics)
            offset += len(segment)

        print(f"\nSegment outline: {len(all_topics)} total topics across {total} chunks\n", flush=True)
        return all_topics

    def _generate_outline_segment(self, chunks, fast_model="gemini"): # This is where the actual outline is being generated.
        request = self.prompt_builder.build_outline(chunks)
        est = (len(request.system_prompt) + len(request.user_prompt)) // 3 # No 2048 because the outline is tiny.

        if fast_model != "gemini":
            self._wait_for_groq_tpm(est, model=LLAMA_MODEL)

        response = self._generate_fast(request, fast_model=fast_model)

        if fast_model != "gemini":
            self._track_groq_usage(response.usage, model=LLAMA_MODEL)

        print("\n" + "=" * 80)
        print("RAW OUTLINE")
        print("=" * 80)
        print(response.raw_output)
        print("=" * 80)

        return OutlineParser().parse(response.raw_output) 

    @staticmethod
    def _get_tail(text: str, n_words: int = 100) -> str:
        words = text.split()
        return " ".join(words[-n_words:]) if len(words) > n_words else text

    @staticmethod
    def _get_head(text: str, n_words: int = 100) -> str:
        words = text.split()
        return " ".join(words[:n_words]) if len(words) > n_words else text

    def _generate_transition(self, prev_tail: str, next_head: str, progress_callback=None) -> str:
        request = self.prompt_builder.build_transition(prev_tail, next_head)
        try:
            response = self._gemini.generate(request, model=Config.GEMINI_FAST_MODEL)
            return response.raw_output.strip()
        except Exception as e:
            msg = f"Transition generation failed: {e}"
            print(f"  {msg}", flush=True)
            if progress_callback:
                progress_callback(msg)
            return ""

    @staticmethod
    def _parse_toc_parts(toc_text: str) -> list[tuple[int, str, list[str]]]:
        import re
        parts = []
        current_part = None
        current_label = ""
        current_headings = []
        for line in toc_text.split("\n"):
            stripped = line.strip()
            m = re.match(r"^### Part\s+([IVXLCDM]+):\s*(.+)$", stripped)
            if m:
                if current_part is not None:
                    parts.append((current_part, current_label, current_headings))
                roman = m.group(1)
                current_label = m.group(2).strip()
                roman_to_int = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
                current_part = roman_to_int.get(roman, len(parts) + 1)
                current_headings = []
                continue
            m2 = re.match(r"^- \[\[#(.+)\]\]$", stripped)
            if m2 and current_part is not None:
                current_headings.append(m2.group(1).strip())
        if current_part is not None:
            parts.append((current_part, current_label, current_headings))
        return parts

    @staticmethod
    def _insert_part_dividers(merged: str, parts: list[tuple[int, str, list[str]]]) -> str:
        if not parts:
            return merged
        heading_to_part = {}
        for part_num, part_label, headings in parts:
            for h in headings:
                heading_to_part[h] = (part_num, part_label)
        ROMAN = ["I", "II", "III", "IV", "V", "VI"]
        lines = merged.split("\n")
        result = []
        current_part = 0
        h3_counter = 0
        for line in lines:
            stripped = line.strip()
            heading_match = re.match(r"^(#{2,3})\s+(.+)$", stripped)
            if heading_match:
                heading_text = heading_match.group(2).strip()
                if heading_text in heading_to_part:
                    new_part_num, part_label = heading_to_part[heading_text]
                    if new_part_num != current_part:
                        h3_counter = 0
                        r = ROMAN[new_part_num - 1] if new_part_num <= 6 else f"Part {new_part_num}"
                        result.append("")
                        result.append("---")
                        result.append("")
                        result.append(f"# ▣ {r}: {part_label}")
                        result.append("")
                        result.append("---")
                        result.append("")
                        current_part = new_part_num
            if stripped.startswith("### ") and current_part > 0:
                h_text = stripped.lstrip("#").strip()
                if h_text not in heading_to_part:
                    h3_counter += 1
                    indent = line[:len(line) - len(line.lstrip())]
                    content = stripped[4:].strip()
                    result.append(f"{indent}### {current_part}.{h3_counter} — {content}")
                    continue
            result.append(line)
        return "\n".join(result)

    @staticmethod
    def _extract_h2_heading(text: str) -> str | None:
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## ") and not stripped.startswith("### "):
                return stripped.lstrip("#").strip()
        return None

    def merge_sections(self, sections, connections_info: list[str] | None = None, progress_callback=None):

        # 1. Calculate target word count (100% preservation)
        teaching_words = sum(len(s.split()) for s in sections)
        target_words = teaching_words
        print(f"  Teaching total: {teaching_words} words across {len(sections)} sections", flush=True)

        # 2. Generate transitions between section boundaries
        transitions = []
        for i in range(len(sections) - 1):
            prev_tail = self._get_tail(sections[i])
            next_head = self._get_head(sections[i + 1])
            transition = self._generate_transition(prev_tail, next_head, progress_callback)
            transitions.append(transition)
            if transition:
                print(f"  Transition {i+1}/{len(sections)-1}: {transition[:80]}...", flush=True)

        # 3. Concatenate sections with transitions inserted between them
        parts = []
        for i, sec in enumerate(sections):
            parts.append(sec)
            if i < len(transitions) and transitions[i]:
                parts.append(transitions[i])
        merged = "\n\n".join(parts)

        # 4. Extract h2 headings (for fallback nav bar)
        section_headings = []
        for sec in sections:
            h = self._extract_h2_heading(sec)
            if h:
                section_headings.append(h)

        # 5. Generate grouped TOC + glossary + sources via LLM
        toc_text = ""
        glossary = ""
        sources = ""
        try:
            struct_request = self.prompt_builder.build_document_structure(merged, target_words)
            struct_response = self._gemini.generate(struct_request, model=Config.GEMINI_FAST_MODEL)
            struct_text = struct_response.raw_output.strip()

            import re
            toc_m = re.search(r"---TOC---\s*(.*?)\s*---ENDTOC---", struct_text, re.DOTALL)
            if toc_m:
                toc_text = toc_m.group(1).strip()
            gl_m = re.search(r"---GLOSSARY---\s*(.*?)\s*---ENDGLOSSARY---", struct_text, re.DOTALL)
            if gl_m:
                glossary = gl_m.group(1).strip()
            src_m = re.search(r"---SOURCES---\s*(.*?)\s*---ENDSOURCES---", struct_text, re.DOTALL)
            if src_m:
                sources = src_m.group(1).strip()

            if toc_text:
                # Strip any existing structural dividers from LLM's TOC
                # (LLM sometimes outputs ## ▣ lines inside TOC markers)
                toc_lines = [l for l in toc_text.split("\n") if "\u25a3" not in l]
                toc_text = "\n".join(toc_lines)
                merged = toc_text + "\n\n" + merged
                print(f"  Grouped TOC: {toc_text.count(chr(10)) + 1} lines", flush=True)
            else:
                toc_text = ""
            if glossary:
                merged = merged + "\n\n---\n\n" + glossary
            if sources:
                merged = merged + "\n\n" + sources
            print(f"  Structure: Glossary ({len(glossary)} chars), Sources ({len(sources)} chars)", flush=True)
        except Exception as e:
            print(f"  Structure generation failed: {e} — falling back to flat nav bar", flush=True)
            toc_text = ""

        # 5b. Insert H1 part dividers and renumber ### subheadings
        if toc_text:
            parts = self._parse_toc_parts(toc_text)
            if parts:
                merged = self._insert_part_dividers(merged, parts)
                print(f"  Part dividers: {len(parts)} part(s), subheadings renumbered", flush=True)
            # Fix LLM sometimes outputting ### 🗺️ Navigation instead of ##
            merged = merged.replace("### 🗺️ Navigation", "## 🗺️ Navigation")
        # 5c. Fallback: flat programmatic nav bar if LLM grouping failed
        if not toc_text:
            toc_lines = ["## 🗺️ Navigation", ""]
            for h in section_headings:
                toc_lines.append(f"- [[#{h}]]")
            flat_toc = "\n".join(toc_lines)
            merged = flat_toc + "\n\n" + merged
            print(f"  Flat nav bar: {len(section_headings)} entries", flush=True)

        # 6. Post-merge validation
        merged_words = len(merged.split())
        ratio = merged_words / target_words if target_words > 0 else 1.0
        print(f"  Merged: {merged_words} words ({ratio:.0%} of teaching total)", flush=True)

        if merged_words < target_words * 0.85:
            print(f"  WARNING: Content dropped below 85% threshold. Falling back to raw concatenation.", flush=True)
            merged = "\n\n".join(sections)
            merged_words = len(merged.split())
            print(f"  Fallback merged: {merged_words} words", flush=True)

        return merged

    def repair_block(self, broken_block: str, issue_category: str, issue_message: str, fast_model="gemini") -> str:
        request = LLMRequest(
            system_prompt=REPAIR_PROMPT,
            user_prompt=f"Issue: [{issue_category}] {issue_message}\n\nBroken block:\n{broken_block}",
        )
        if fast_model != "gemini":
            self._wait_for_groq_tpm(500, model=LLAMA_MODEL)
        response = self._generate_fast(request, fast_model=fast_model)
        if fast_model != "gemini":
            self._track_groq_usage(response.usage, model=LLAMA_MODEL)
        return response.raw_output

    def _collect_topic_text(self, topic, chunks):
        selected = []

        for index in topic.source_chunks:
            if 1 <= index <= len(chunks):
                selected.append(chunks[index - 1].text)

        return "\n\n".join(selected)