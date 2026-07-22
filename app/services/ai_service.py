import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
}  # per-model on Groq on_demand tier


class AIService:
    def __init__(self):
        self._groq = GroqClient()
        self._use_gemini = Config.LLM_PROVIDER == "gemini"
        self._gemini = GeminiClient() if self._use_gemini else None

        self.prompt_builder = PromptBuilder()
        self._groq_tpm_windows: dict[str, list] = {}
        self._groq_tpm_lock = threading.Lock()

    def _generate_fast(self, request):
        """Route FAST_MODEL calls to Gemini or Groq based on LLM_PROVIDER."""
        if self._use_gemini:
            return self._gemini.generate(request, model=Config.FAST_MODEL)
        return self._groq.generate(request, model=Config.FAST_MODEL)

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

    def _run_extraction(self, topic_index: int, topic, chunks):
        """Run extraction for one topic. Meant to be called from threads."""

        source_text = self._collect_topic_text(topic, chunks)
        extraction_request = self.prompt_builder.build_extraction(source_text)
        est = (len(extraction_request.system_prompt) + len(extraction_request.user_prompt)) // 3 + 2048
        if not self._use_gemini:
            self._wait_for_groq_tpm(est, model=Config.FAST_MODEL)
        raw_response = self._generate_fast(extraction_request)
        if not self._use_gemini:
            self._track_groq_usage(raw_response.usage, model=Config.FAST_MODEL)
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
        """Run teaching for one topic. Meant to be called from threads."""
        req = self.prompt_builder.build_teaching(
            knowledge=knowledge,
            outline=outline,
            current_topic=topic,
            topic_index=topic_index,
            total_topics=total_topics,
        )
        req.max_tokens = 1500
        est = (len(req.system_prompt) + len(req.user_prompt)) // 3 + 1500
        self._wait_for_groq_tpm(est, model=Config.REASONING_MODEL)
        response = self._groq.generate(req, model=Config.REASONING_MODEL)
        self._track_groq_usage(response.usage, model=Config.REASONING_MODEL)
        return topic_index, response.raw_output

    def generate_from_chunks(self, chunks, outline):
        total_topics = len(outline)

        # ---- Phase 1: All extractions in parallel ----
        print(f"\n--- Running {len(outline)} extractions in parallel ---")
        extraction_results: list = [None] * len(outline)

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_map = {
                executor.submit(self._run_extraction, idx, topic, chunks): idx
                for idx, topic in enumerate(outline)
            }

            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    _, topic, knowledge, source_text = future.result()
                    extraction_results[idx] = (topic, knowledge, source_text)
                    self._print_extraction(idx, topic, knowledge, source_text)
                except Exception as e:
                    print(f"Extraction failed for topic {idx} ({outline[idx].title}): {e}")
                    extraction_results[idx] = None

        # ---- Phase 2: Parallel teaching (independent now that previous_notes is removed) ----
        print(f"\n--- Running {len(outline)} teaching calls in parallel (2 workers) ---")
        teaching_results: list = [None] * len(outline)

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

            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    _, output = future.result()
                    teaching_results[idx] = output
                except Exception as e:
                    print(f"Teaching failed for topic {idx} ({outline[idx].title}): {e}")
                    teaching_results[idx] = None

        # Collect outputs in order, extract connections for merge pass
        outputs = []
        connections_list = []
        for idx, result in enumerate(extraction_results):
            if result is not None and teaching_results[idx] is not None:
                outputs.append(teaching_results[idx])
                _, knowledge, _ = result
                if knowledge.connections:
                    connections_list.extend(knowledge.connections)

        return outputs, connections_list

    def generate_outline(self, chunks):
        request = self.prompt_builder.build_outline(chunks)
        est = (len(request.system_prompt) + len(request.user_prompt)) // 3
        if not self._use_gemini:
            self._wait_for_groq_tpm(est, model=Config.FAST_MODEL)
        response = self._generate_fast(request)
        if not self._use_gemini:
            self._track_groq_usage(response.usage, model=Config.FAST_MODEL)

        print("\n" + "=" * 80)
        print("RAW OUTLINE")
        print("=" * 80)
        print(response.raw_output)
        print("=" * 80)

        return OutlineParser().parse(response.raw_output)

    def merge_sections(self, sections, connections_info: list[str] | None = None):
        max_output = 4096

        connections_text = None
        if connections_info:
            connections_text = "\n".join(f"- {c}" for c in connections_info)

        def _try_merge(secs):
            request = self.prompt_builder.build_merge(secs, connections_info=connections_text)
            request.max_tokens = max_output
            est = (len(request.system_prompt) + len(request.user_prompt)) // 3 + max_output
            self._wait_for_groq_tpm(est, model=Config.REASONING_MODEL)
            response = self._groq.generate(request, model=Config.REASONING_MODEL)
            self._track_groq_usage(response.usage, model=Config.REASONING_MODEL)
            return response.raw_output

        # For 4+ sections, use hierarchical merge (groups of 2-3, then merge results)
        if len(sections) > 4:
            print(f"  Using hierarchical merge for {len(sections)} sections")
            merged = []
            group_size = 3
            for i in range(0, len(sections), group_size):
                group = sections[i:i + group_size]
                if len(group) == 1:
                    merged.append(group[0])
                else:
                    merged.append(_try_merge(group))
            if len(merged) > 1:
                return _try_merge(merged)
            return merged[0]

        # For 3 or fewer, try single merge first
        try:
            return _try_merge(sections)
        except Exception as e:
            if "413" not in str(e) and "rate_limit_exceeded" not in str(e):
                raise
            print("  Merge too large, retrying with truncated sections")
            truncated = [s[:max(len(s) // 2, 100)] for s in sections]
            return _try_merge(truncated)

    def repair_block(self, broken_block: str, issue_category: str, issue_message: str) -> str:
        request = LLMRequest(
            system_prompt=REPAIR_PROMPT,
            user_prompt=f"Issue: [{issue_category}] {issue_message}\n\nBroken block:\n{broken_block}",
        )
        if not self._use_gemini:
            self._wait_for_groq_tpm(500, model=Config.FAST_MODEL)
        response = self._generate_fast(request)
        if not self._use_gemini:
            self._track_groq_usage(response.usage, model=Config.FAST_MODEL)
        return response.raw_output

    def _collect_topic_text(self, topic, chunks):
        selected = []

        for index in topic.source_chunks:
            if 1 <= index <= len(chunks):
                selected.append(chunks[index - 1].text)

        return "\n\n".join(selected)