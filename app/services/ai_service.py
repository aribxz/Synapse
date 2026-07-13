import time
from pprint import pprint

from app.llm.client import GroqClient
from app.llm.gemini_client import GeminiClient
from app.llm.prompt_builder import PromptBuilder
from app.llm.outline_parser import OutlineParser
from app.llm.extraction_parser import ExtractionParser
from config import Config


class AIService:
    def __init__(self):
        provider = Config.LLM_PROVIDER.lower()
        if provider == "gemini":
            self.client = GeminiClient()
        else:
            self.client = GroqClient()
        self.prompt_builder = PromptBuilder()
        self._tpm_window = []  # (timestamp, tokens) for rolling TPM tracking

    def _wait_for_tpm(self, estimated_tokens: int = 1000):
        """Delay if we'd exceed the 6000 TPM limit."""
        now = time.time()
        # Drop entries older than 60 seconds
        self._tpm_window = [(ts, t) for ts, t in self._tpm_window if now - ts < 60]
        total_in_window = sum(t for _, t in self._tpm_window)

        if total_in_window + estimated_tokens > 5000:  # 1000 headroom under 6000
            sleep_for = max(15, 60 - (now - self._tpm_window[0][0])) if self._tpm_window else 15
            print(f"TPM limit approaching ({total_in_window}/{6000}). Waiting {sleep_for:.0f}s...")
            time.sleep(sleep_for)
            self._tpm_window = []
        else:
            time.sleep(3)  # Small delay between any two calls

    def _track_usage(self, usage: dict | None):
        if usage and "total_tokens" in usage:
            self._tpm_window.append((time.time(), usage["total_tokens"]))

    def generate_from_chunks(self, chunks, outline):
        outputs = []
        previous_notes = None
        total_topics = len(outline)

        for topic_index, topic in enumerate(outline):
            source_text = self._collect_topic_text(topic, chunks)

            try:
                extraction_request = self.prompt_builder.build_extraction(source_text)
                self._wait_for_tpm(2000)
                raw_response = self.client.generate(extraction_request, model=Config.FAST_MODEL)
                self._track_usage(raw_response.usage)
                raw_json = raw_response.raw_output

                knowledge = ExtractionParser().parse(raw_json)

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

                teaching_request = self.prompt_builder.build_teaching(
                    knowledge=knowledge,
                    outline=outline,
                    current_topic=topic,
                    previous_notes=previous_notes,
                    topic_index=topic_index,
                    total_topics=total_topics,
                )

                self._wait_for_tpm(3000)
                response = self.client.generate(teaching_request, model=Config.FAST_MODEL)
                self._track_usage(response.usage)

                outputs.append(response.raw_output)
                # Accumulate ALL previous notes so each section sees full context
                if previous_notes is None:
                    previous_notes = response.raw_output
                else:
                    previous_notes = previous_notes + "\n\n---\n\n" + response.raw_output

            except Exception as e:
                print(f"Generation failed: {e}")
                continue

        return outputs

    def generate_outline(self, chunks):
        request = self.prompt_builder.build_outline(chunks)
        self._wait_for_tpm(3000)
        response = self.client.generate(request, model=Config.FAST_MODEL)
        self._track_usage(response.usage)
        print("\n" + "=" * 80)
        print("RAW OUTLINE")
        print("=" * 80)
        print(response.raw_output)
        print("=" * 80)
        return OutlineParser().parse(response.raw_output)

    def merge_sections(self, sections):
        request = self.prompt_builder.build_merge(sections)
        self._wait_for_tpm(4000)
        response = self.client.generate(request, model=Config.FAST_MODEL)
        self._track_usage(response.usage)
        return response.raw_output

    def _collect_topic_text(self, topic, chunks):
        selected = []

        for index in topic.source_chunks:
            if 1 <= index <= len(chunks):
                selected.append(chunks[index - 1].text)

        return "\n\n".join(selected)
