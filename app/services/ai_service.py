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


class AIService:
    def __init__(self):
        provider = Config.LLM_PROVIDER.lower()
        if provider == "gemini":
            self.client = GeminiClient()
        else:
            self.client = GroqClient()

        self.prompt_builder = PromptBuilder()
        self._tpm_window = [] # Contains information about time and tokens.
        self._tpm_lock = threading.Lock() # Makes sure that two or more workers are not updating tpm window simultaneously.

    def _wait_for_tpm(self, estimated_tokens: int = 1000):
        """Delay if we'd exceed the 6000 TPM limit. Thread-safe."""

        with self._tpm_lock:
            now = time.time()
            self._tpm_window = [(ts, t) for ts, t in self._tpm_window if now - ts < 60]
            total_in_window = sum(t for _, t in self._tpm_window)

            if total_in_window + estimated_tokens > 5500:
                sleep_for = max(5, 60 - (now - self._tpm_window[0][0])) if self._tpm_window else 5
                print(f"TPM limit approaching ({total_in_window}/{6000}). Waiting {sleep_for:.0f}s...")
                time.sleep(sleep_for)
                self._tpm_window = []

    def _track_usage(self, usage: dict | None): # Records completed requests.
        if usage and "total_tokens" in usage: # Checks is usage is none and tokens exists. Usage is returned by the LLM.
            with self._tpm_lock: # Using the lock ensures only one thread updates the shared list at a time.
                self._tpm_window.append((time.time(), usage["total_tokens"]))

    def _run_extraction(self, topic_index: int, topic, chunks):
        """Run extraction for one topic. Meant to be called from threads."""

        source_text = self._collect_topic_text(topic, chunks)
        extraction_request = self.prompt_builder.build_extraction(source_text)
        est = (len(extraction_request.system_prompt) + len(extraction_request.user_prompt)) // 3 + 2048
        self._wait_for_tpm(est)
        raw_response = self.client.generate(extraction_request, model=Config.FAST_MODEL)
        self._track_usage(raw_response.usage) # Records new token limits.
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

    def generate_from_chunks(self, chunks, outline):
        outputs = []
        previous_notes = None
        total_topics = len(outline)

        # ---- Phase 1: All extractions in parallel ----
        print(f"\n--- Running {len(outline)} extractions in parallel ---")
        results: list = [None] * len(outline) # A list of size of total outline topics.

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_map = {
                executor.submit(self._run_extraction, idx, topic, chunks): idx # Submit assigns work to the worker. It also assigns future for every worker.
                for idx, topic in enumerate(outline)
            }

            for future in as_completed(future_map): # as_completed returns in order of whoever finishes first.
                idx = future_map[future] # We look up the index from the future.

                try:
                    _, topic, knowledge, source_text = future.result() # Takes the values, ignores the index because we already have it.
                    results[idx] = (topic, knowledge, source_text) # Save it at the index taken before.

                    """Without indexes the order would get messed up which will affect the teaching phase."""
                    self._print_extraction(idx, topic, knowledge, source_text)

                except Exception as e:
                    print(f"Extraction failed for topic {idx} ({outline[idx].title}): {e}")
                    results[idx] = None # If something fails, skip it.

        # ---- Phase 2: Sequential teaching ----
        print("\n--- Running teaching phase sequentially ---")

        for topic_index in range(len(outline)):
            result = results[topic_index] # Retrives values.
            if result is None:
                print(f"Skipping teaching for topic {topic_index}: extraction failed")
                continue

            topic, knowledge, _ = result # Unpacks the stored tuple.

            prev_for_topic = previous_notes
            if prev_for_topic and len(prev_for_topic) > 3000:
                prev_for_topic = "..." + prev_for_topic[-3000:]

            def _do_teaching(prev):
                req = self.prompt_builder.build_teaching(
                    knowledge=knowledge,
                    outline=outline,
                    current_topic=topic,
                    previous_notes=prev,
                    topic_index=topic_index,
                    total_topics=total_topics,
                )
                req.max_tokens = 1500
                est = (len(req.system_prompt) + len(req.user_prompt)) // 3 + 1500
                self._wait_for_tpm(est)
                return self.client.generate(req, model=Config.FAST_MODEL)

            try:
                response = _do_teaching(prev_for_topic)
            except Exception as e:
                if "413" in str(e) or "rate_limit_exceeded" in str(e):
                    print(f"  Teaching too large, retrying with truncated context")
                    prev_for_topic = "..." + (prev_for_topic[-2000:] if prev_for_topic else "")
                    try:
                        response = _do_teaching(prev_for_topic)
                    except Exception as e2:
                        print(f"Teaching failed for topic {topic_index} ({topic.title}): {e2}")
                        continue
                else:
                    print(f"Teaching failed for topic {topic_index} ({topic.title}): {e}")
                    continue

            self._track_usage(response.usage)

            outputs.append(response.raw_output)

            if previous_notes is None:
                previous_notes = response.raw_output
            else:
                previous_notes = previous_notes + "\n\n---\n\n" + response.raw_output

        return outputs

    def generate_outline(self, chunks):
        request = self.prompt_builder.build_outline(chunks)
        est = (len(request.system_prompt) + len(request.user_prompt)) // 3
        self._wait_for_tpm(est)
        response = self.client.generate(request, model=Config.FAST_MODEL)
        self._track_usage(response.usage)

        print("\n" + "=" * 80)
        print("RAW OUTLINE")
        print("=" * 80)
        print(response.raw_output)
        print("=" * 80)

        return OutlineParser().parse(response.raw_output)

    def merge_sections(self, sections):
        max_output = 1500

        def _try_merge(secs):
            request = self.prompt_builder.build_merge(secs)
            request.max_tokens = max_output
            est = (len(request.system_prompt) + len(request.user_prompt)) // 3 + max_output
            self._wait_for_tpm(est)
            response = self.client.generate(request, model=Config.FAST_MODEL)
            self._track_usage(response.usage)
            return response.raw_output

        try:
            return _try_merge(sections)
        except Exception as e:
            if "413" not in str(e) and "rate_limit_exceeded" not in str(e):
                raise
            print("  Merge too large, retrying with half-size sections")
            truncated = [s[:max(len(s) // 2, 100)] for s in sections]
            return _try_merge(truncated)

    def repair_block(self, broken_block: str, issue_category: str, issue_message: str) -> str:
        request = LLMRequest(
            system_prompt=REPAIR_PROMPT,
            user_prompt=f"Issue: [{issue_category}] {issue_message}\n\nBroken block:\n{broken_block}",
        )
        self._wait_for_tpm(500)
        response = self.client.generate(request, model=Config.FAST_MODEL)
        self._track_usage(response.usage)
        return response.raw_output

    def _collect_topic_text(self, topic, chunks):
        selected = []

        for index in topic.source_chunks:
            if 1 <= index <= len(chunks):
                selected.append(chunks[index - 1].text)

        return "\n\n".join(selected)