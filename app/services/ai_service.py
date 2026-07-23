import json
import time
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

    def _generate_fast(self, request, fast_model="gemini"):
        if fast_model == "gemini":
            return self._gemini.generate(request, model=Config.GEMINI_FAST_MODEL)
        return self._groq.generate(request, model=LLAMA_MODEL)

    def _tpm_key(self, model: str) -> str:
        return GROQ_TPM_LIMITS.get(model, "default")

    def _wait_for_groq_tpm(self, estimated_tokens: int = 1000, model: str = ""):
        """Delay if we'd exceed the Groq TPM limit for the given model. Thread-safe.
        Uses a separate window per model since Groq enforces per-model TPM."""
        tpm_limit = GROQ_TPM_LIMITS.get(model, 8000)
        key = self._tpm_key(model)
        with self._groq_tpm_lock:
            now = time.time()
            window = self._groq_tpm_windows.setdefault(key, [])
            self._groq_tpm_windows[key] = [(ts, t) for ts, t in window if now - ts < 60]
            total_in_window = sum(t for _, t in self._groq_tpm_windows[key])

            if total_in_window + estimated_tokens > tpm_limit * 0.9:
                sleep_for = max(5, 60 - (now - self._groq_tpm_windows[key][0][0])) if self._groq_tpm_windows[key] else 5
                print(f"  Groq TPM limit ({tpm_limit}) for {model}. Waiting {sleep_for:.0f}s...")
                time.sleep(sleep_for)
                self._groq_tpm_windows[key] = []

    def _track_groq_usage(self, usage: dict | None, model: str = ""):
        if usage and "total_tokens" in usage:
            key = self._tpm_key(model)
            with self._groq_tpm_lock:
                window = self._groq_tpm_windows.setdefault(key, [])
                window.append((time.time(), usage["total_tokens"]))

    def _run_extraction(self, topic_index: int, topic, chunks, fast_model="gemini"):
        source_text = self._collect_topic_text(topic, chunks)
        extraction_request = self.prompt_builder.build_extraction(source_text)
        est = (len(extraction_request.system_prompt) + len(extraction_request.user_prompt)) // 3 + 2048
        if fast_model != "gemini":
            self._wait_for_groq_tpm(est, model=LLAMA_MODEL)
        raw_response = self._generate_fast(extraction_request, fast_model=fast_model)
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
        """Run teaching for one topic. Falls back through OSS-120B → Llama 3.3 70B → Gemini."""
        req = self.prompt_builder.build_teaching(
            knowledge=knowledge,
            outline=outline,
            current_topic=topic,
            topic_index=topic_index,
            total_topics=total_topics,
        )
        kd = {k: v for k, v in asdict(knowledge).items() if k != "connections"}
        knowledge_size = len(json.dumps(kd, separators=(",", ":")))
        req.max_tokens = min(4096, max(1500, 1500 + knowledge_size // 8))
        est = (len(req.system_prompt) + len(req.user_prompt)) // 3 + req.max_tokens

        model_used = Config.REASONING_MODEL
        self._wait_for_groq_tpm(est, model=Config.REASONING_MODEL)
        try:
            response = self._groq.generate(req, model=Config.REASONING_MODEL)
            self._track_groq_usage(response.usage, model=Config.REASONING_MODEL)
            print(f"  Topic {topic_index} ({topic.title}): served by {model_used}", flush=True)
            return topic_index, response.raw_output
        except Exception as e:
            if "413" not in str(e) and "rate_limit_exceeded" not in str(e):
                raise
            msg = f"OSS-120B rate limit hit for '{topic.title}', switching to Llama 3.3 70B"
            print(f"  {msg}", flush=True)
            with self._fallback_msgs_lock:
                self._fallback_msgs.append(msg)

        model_used = LLAMA_MODEL
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

        model_used = Config.GEMINI_FAST_MODEL
        response = self._gemini.generate(req, model=Config.GEMINI_FAST_MODEL)
        print(f"  Topic {topic_index} ({topic.title}): served by {model_used}", flush=True)
        return topic_index, response.raw_output

    def generate_from_chunks(self, chunks, outline, fast_model="gemini"):
        total_topics = len(outline)

        # ---- Phase 1: All extractions in parallel ----
        print(f"\n--- Running {len(outline)} extractions in parallel (fast model: {fast_model}) ---")
        extraction_results: list = [None] * len(outline)

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_map = {
                executor.submit(self._run_extraction, idx, topic, chunks, fast_model): idx
                for idx, topic in enumerate(outline)
            }

            completed = 0
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    _, topic, knowledge, source_text = future.result()
                    extraction_results[idx] = (topic, knowledge, source_text)
                    self._print_extraction(idx, topic, knowledge, source_text)
                except Exception as e:
                    print(f"Extraction failed for topic {idx} ({outline[idx].title}): {e}")
                    extraction_results[idx] = None
                completed += 1
                yield "progress", f"Extracting: {outline[idx].title}", outline[idx].title, (completed / total_topics) * 40

        # ---- Phase 2: Parallel teaching (independent now that previous_notes is removed) ----
        print(f"\n--- Running {len(outline)} teaching calls in parallel (2 workers) ---")
        teaching_results: list = [None] * len(outline)
        valid_count = sum(1 for r in extraction_results if r is not None)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_map = {}
            for idx, result in enumerate(extraction_results):
                if result is None:
                    print(f"Skipping teaching for topic {idx}: extraction failed")
                    continue
                topic, knowledge, _ = result
                future = executor.submit(
                    self._run_teaching, idx, topic, outline, knowledge, total_topics
                )
                future_map[future] = idx

            completed = 0
            for future in as_completed(future_map):
                idx = future_map[future]
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

        # Collect outputs in order, extract connections for merge pass
        outputs = []
        connections_list = []
        for idx, result in enumerate(extraction_results):
            if result is not None and teaching_results[idx] is not None:
                tw = len(teaching_results[idx].split())
                print(f"  Topic {idx} ({outline[idx].title}): {len(teaching_results[idx])} chars / {tw} words", flush=True)
                outputs.append(teaching_results[idx])
                _, knowledge, _ = result
                if knowledge.connections:
                    connections_list.extend(knowledge.connections)

        return outputs, connections_list

    def generate_outline(self, chunks, fast_model="gemini"):
        total = len(chunks)
        if total <= 20:
            return self._generate_outline_segment(chunks, fast_model)

        # Split large inputs into segments so each one stays in the model's
        # comfortable topic range (5-9 topics per segment when ≤20 chunks).
        import math
        num_segments = min(5, max(2, (total + 10) // 20))
        seg_size = math.ceil(total / num_segments)
        all_topics = []
        offset = 0
        for i in range(0, total, seg_size):
            segment = chunks[i:i + seg_size]
            seg_topics = self._generate_outline_segment(segment, fast_model)
            for t in seg_topics:
                t.source_chunks = [c + offset for c in t.source_chunks]
            all_topics.extend(seg_topics)
            offset += len(segment)

        print(f"\nSegment outline: {len(all_topics)} total topics across {total} chunks\n", flush=True)
        return all_topics

    def _generate_outline_segment(self, chunks, fast_model="gemini"):
        request = self.prompt_builder.build_outline(chunks)
        est = (len(request.system_prompt) + len(request.user_prompt)) // 3
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
    def _extract_h2_heading(text: str) -> str | None:
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## ") and not stripped.startswith("### "):
                return stripped.lstrip("#").strip()
        return None

    def merge_sections(self, sections, connections_info: list[str] | None = None, progress_callback=None, source_labels: list[str] | None = None, sections_per_source: list[int] | None = None):
        ROMAN = ["I", "II", "III", "IV", "V", "VI"]

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

        # 4. Build navigation bar grouped by source
        toc_lines = ["## 🗺️ Navigation", ""]
        if source_labels and sections_per_source:
            idx = 0
            for group_i, (label, cnt) in enumerate(zip(source_labels, sections_per_source)):
                if cnt == 0:
                    continue
                part = ROMAN[group_i] if group_i < len(ROMAN) else f"Part {group_i+1}"
                toc_lines.append(f"### {part}: {label}")
                for h_idx in range(idx, min(idx + cnt, len(sections))):
                    heading = self._extract_h2_heading(sections[h_idx])
                    if heading:
                        toc_lines.append(f"- [[#{heading}]]")
                idx += cnt
                toc_lines.append("")
        else:
            for sec in sections:
                heading = self._extract_h2_heading(sec)
                if heading:
                    toc_lines.append(f"- [[#{heading}]]")

        toc = "\n".join(toc_lines).rstrip()
        merged = toc + "\n\n" + merged
        num_parts = len(source_labels) if source_labels is not None else 1
        print(f"  Navigation: grouped into {num_parts} part(s)", flush=True)

        # 5. Generate glossary + sources (additive only, no body rewriting)
        try:
            struct_request = self.prompt_builder.build_document_structure(merged, target_words)
            struct_response = self._gemini.generate(struct_request, model=Config.GEMINI_FAST_MODEL)
            struct_text = struct_response.raw_output.strip()

            glossary = ""
            sources = ""
            current_section = ""
            for line in struct_text.split("\n"):
                if line.strip() == "---GLOSSARY---":
                    current_section = "glossary"
                elif line.strip() == "---SOURCES---":
                    current_section = "sources"
                elif current_section == "glossary":
                    glossary += line + "\n"
                elif current_section == "sources":
                    sources += line + "\n"

            glossary = glossary.strip()
            sources = sources.strip()

            if glossary:
                merged = merged + "\n\n---\n\n" + glossary
            if sources:
                merged = merged + "\n\n" + sources

            print(f"  Structure: Glossary ({len(glossary)} chars), Sources ({len(sources)} chars)", flush=True)
        except Exception as e:
            print(f"  Structure generation failed: {e} — continuing with concatenation", flush=True)

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