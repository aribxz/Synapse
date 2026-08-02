import threading
import time

from app.services.extraction_service import ExtractionService
from app.processing.document_processor import DocumentProcessor
from app.services.chunking_service import ChunkingService
from app.services.ai_service import AIService
from app.rendering.markdown_renderer import MarkdownRenderer
from app.services.export_service import ExportService
from app.services.quality_gate import QualityGate
from app.models.enums import ProcessingStatus, SourceType


class PipelineService:

    def __init__(self):

        self.extraction = ExtractionService()
        self.processing = DocumentProcessor()
        self.chunking = ChunkingService()
        self.ai = AIService()
        self.renderer = MarkdownRenderer()
        self.quality_gate = QualityGate(ai_service=self.ai)
        self.exporter = ExportService()

    def _heartbeat(self, fn, pct, msg, interval=15):
        """Run a blocking call in a background thread, yielding a status
        heartbeat every `interval` seconds so gunicorn's worker timeout and
        Cloudflare's idle timeout never kill a long-running silent step.

        Returns the blocking call's result via StopIteration.value.
        """
        box = {}
        done = threading.Event()

        def runner():
            try:
                box["result"] = fn()
            except Exception as exc:
                box["error"] = exc
            finally:
                done.set()

        threading.Thread(target=runner, daemon=True).start()

        last = time.monotonic()
        while not done.is_set():
            now = time.monotonic()
            if now - last >= interval:
                yield pct, msg, ""
                last = now
            time.sleep(0.5)

        if "error" in box:
            raise box["error"]
        return box["result"]

    def process(self, collection, fast_model="gemini"):
        print(f"\n=== Pipeline started (fast model: {fast_model}) ===", flush=True)

        yield 2, "Starting pipeline...", ""

        yield 5, "Extracting content from sources...", ""
        collection = yield from self._heartbeat( # From links/pdfs to transcripts.
            lambda: self.extraction.process(collection),
            pct=5,
            msg="Still extracting content...",
        )

        failed_sources = [s for s in collection.sources if s.status == ProcessingStatus.FAILED]
        total_sources = len(collection.sources)

        if failed_sources:
            yield 5, f"Extraction finished — {len(failed_sources)} of {total_sources} source(s) failed to extract", ""
            for s in failed_sources:
                reason = (s.error or "no extractable text found").strip()
                yield 5, f"Could not extract: {s.title} — {reason[:80]}", s.title
        else:
            yield 5, f"Extraction complete — all {total_sources} source(s) extracted successfully", ""

        yield 8, "Processing documents...", ""
        collection = self.processing.process(collection) # From transcripts to clean text.

        generated_sections = []
        all_connections = []

        valid_sources = [s for s in collection.sources if s.raw_content and len(s.raw_content.strip()) >= 200] # Only sources that were extracted correctly.
        total_valid = len(valid_sources)
        source_idx = 0

        # Processing:
        for source in collection.sources: # Loop through each source.
            if (not source.raw_content
                or len(source.raw_content.strip()) < 200
            ):
                source.status = ProcessingStatus.FAILED

                if not source.error:
                    source.error = "No extractable text found."

                print(f"Skipping {source.title}: {source.error}", flush=True)

                error_detail = source.metadata.get("error_detail")
                if error_detail:
                    print(f"  Detail: {error_detail}", flush=True)

                if source.source_type == SourceType.YOUTUBE:
                    generated_sections.append(
                        f"## {source.title}\n\n"
                        f"**Could not extract the transcript from this video:** {source.error}\n\n"
                        "_If this keeps happening, get the transcript manually: on YouTube "
                        "click '...' under the video, select 'Show transcript', copy the text, "
                        "save it as a .txt file, and upload it here._"
                    )
                else:
                    generated_sections.append(
                        f"## {source.title}\n\n_Could not extract text from this source: {source.error}_"
                    )

                continue

            if total_valid > 0:
                source_start = 10 + (source_idx / total_valid) * 68
                source_end = 10 + ((source_idx + 1) / total_valid) * 68

            else:
                source_start, source_end = 10, 78

            source_idx += 1

            yield int(source_start), f"Chunking: {source.title}", source.title # Source start and end are helping us give info to the frontend.
            chunks = self.chunking.process(source) # Converts the cleaned texts into different chunks.

            if not chunks:
                generated_sections.append(f"## {source.title}\n\nNo content was available to chunk from this file.")
                continue

            yield int(source_start + 6), f"Generating outline for {source.title}", source.title # Again, progress bar.

            try:
                outline = yield from self._heartbeat( # It decides what chunks are related.
                    lambda: self.ai.generate_outline(chunks, fast_model=fast_model),
                    pct=int(source_start + 6),
                    msg=f"Still generating outline for {source.title}...",
                )

            except Exception as exc:
                generated_sections.append(f"## {source.title}\n\nAI generation failed: {exc}")
                continue

            ai_start = source_start + 12
            ai_end = source_end

            sub_gen = self.ai.generate_from_chunks(chunks, outline, fast_model=fast_model) # Generator inside of a generator.

            while True:
                try:
                    kind, msg, title, pct_in_ai = next(sub_gen) # We directly calls next(sub_gen).

                    if kind == "progress":
                        global_pct = int(ai_start + (pct_in_ai / 100) * (ai_end - ai_start))
                        yield global_pct, msg, title # Again, progress bar.

                except StopIteration as e:
                    generated, connections = e.value
                    generated_sections.extend(generated)
                    all_connections.extend(connections)
                    break

        # Merging:
        yield 78, "Merging sections...", ""

        if not generated_sections:
            fallback_text = "\n\n".join( # Simple join.
                f"## {source.title}\n\n{source.raw_content[:4000]}"
                for source in collection.sources
                if source.raw_content
            )

            merged_document = fallback_text or "No content could be generated from the provided input."

        else:
            merge_msgs = []

            def on_merge_progress(msg): 
                merge_msgs.append(msg)

            try:
                merged_document = yield from self._heartbeat( # Merges the glossary, nav bar etc.
                    lambda: self.ai.merge_sections(
                        generated_sections,
                        connections_info=all_connections,
                        progress_callback=on_merge_progress,
                    ),
                    pct=78,
                    msg="Still merging sections...",
                )

                for m in merge_msgs:
                    yield 78, m, ""

                # Pure Statistics
                teaching_total = sum(len(s.split()) for s in generated_sections)
                merged_words = len(merged_document.split())
                ratio = merged_words / teaching_total * 100 if teaching_total > 0 else 0

                print("\n========== MERGE STATS ==========", flush=True)
                print(f"Teaching total: {teaching_total} words", flush=True)
                print(f"Merged: {merged_words} words ({ratio:.0f}% preserved)", flush=True)
                print(f"Characters: {len(merged_document)}", flush=True)
                print("=================================\n", flush=True)

            except Exception as exc:
                merged_document = "\n\n".join(generated_sections)
                print(f"Merge failed: {exc}", flush=True)

        yield 85, "Rendering markdown...", ""
        markdown = self.renderer.render([merged_document]) # Internal document to polished markdown.

        yield 90, "Running quality checks...", ""
        markdown = yield from self._heartbeat( # Final inspection.
            lambda: self.quality_gate.run(markdown, fast_model=fast_model),
            pct=90,
            msg="Still running quality checks...",
        )

        yield 95, "Exporting...", ""
        output_file = self.exporter.export(markdown, "notes") # Export service.

        yield 100, "Done! Downloading notes...", ""
        return output_file