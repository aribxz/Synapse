from app.services.extraction_service import ExtractionService
from app.processing.document_processor import DocumentProcessor
from app.services.chunking_service import ChunkingService
from app.services.ai_service import AIService
from app.rendering.markdown_renderer import MarkdownRenderer
from app.services.export_service import ExportService
from app.services.quality_gate import QualityGate
from app.models.enums import ProcessingStatus


class PipelineService:

    def __init__(self):

        self.extraction = ExtractionService()
        self.processing = DocumentProcessor()
        self.chunking = ChunkingService()
        self.ai = AIService()
        self.renderer = MarkdownRenderer()
        self.quality_gate = QualityGate(ai_service=self.ai)
        self.exporter = ExportService()

    def process(self, collection, fast_model="gemini"):
        print(f"\n=== Pipeline started (fast model: {fast_model}) ===", flush=True)

        yield 2, "Starting pipeline...", ""

        yield 5, "Extracting content from sources...", ""
        collection = self.extraction.process(collection)

        yield 8, "Processing documents...", ""
        collection = self.processing.process(collection)

        generated_sections = []
        all_connections = []

        valid_sources = [s for s in collection.sources if s.raw_content and len(s.raw_content.strip()) >= 200]
        total_valid = len(valid_sources)
        source_idx = 0

        for source in collection.sources:
            if (not source.raw_content
                or len(source.raw_content.strip()) < 200
            ):
                source.status = ProcessingStatus.FAILED
                source.error = "No extractable text found."

                print(f"Skipping {source.title}: no usable text extracted.", flush=True)
                generated_sections.append(f"## {source.title}\n\n_Could not extract text from this source._")

                continue

            if total_valid > 0:
                source_start = 10 + (source_idx / total_valid) * 68
                source_end = 10 + ((source_idx + 1) / total_valid) * 68
            else:
                source_start, source_end = 10, 78
            source_idx += 1

            yield int(source_start), f"Chunking: {source.title}", source.title
            chunks = self.chunking.process(source)

            if not chunks:
                generated_sections.append(f"## {source.title}\n\nNo content was available to chunk from this file.")
                continue

            yield int(source_start + 6), f"Generating outline for {source.title}", source.title
            try:
                outline = self.ai.generate_outline(chunks, fast_model=fast_model)
            except Exception as exc:
                generated_sections.append(f"## {source.title}\n\nAI generation failed: {exc}")
                continue

            ai_start = source_start + 12
            ai_end = source_end

            sub_gen = self.ai.generate_from_chunks(chunks, outline, fast_model=fast_model)
            while True:
                try:
                    kind, msg, title, pct_in_ai = next(sub_gen)
                    if kind == "progress":
                        global_pct = int(ai_start + (pct_in_ai / 100) * (ai_end - ai_start))
                        yield global_pct, msg, title
                except StopIteration as e:
                    generated, connections = e.value
                    generated_sections.extend(generated)
                    all_connections.extend(connections)
                    break

        yield 78, "Merging sections...", ""

        if not generated_sections:
            fallback_text = "\n\n".join(
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
                merged_document = self.ai.merge_sections(
                    generated_sections,
                    connections_info=all_connections,
                    progress_callback=on_merge_progress,
                )
                for m in merge_msgs:
                    yield 78, m, ""
                print("\n========== MERGE STATS ==========", flush=True)
                print(f"Characters: {len(merged_document)}", flush=True)
                print(f"Words: {len(merged_document.split())}", flush=True)
                print("=================================\n", flush=True)
            except Exception as exc:
                merged_document = "\n\n".join(generated_sections)
                print(f"Merge failed: {exc}", flush=True)

        yield 85, "Rendering markdown...", ""
        markdown = self.renderer.render([merged_document])

        yield 90, "Running quality checks...", ""
        markdown = self.quality_gate.run(markdown, fast_model=fast_model)

        yield 95, "Exporting...", ""
        output_file = self.exporter.export(markdown, "notes")

        yield 100, "Done! Downloading notes...", ""
        return output_file

