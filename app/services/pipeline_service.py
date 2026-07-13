from app.services.extraction_service import ExtractionService
from app.processing.document_processor import DocumentProcessor
from app.services.chunking_service import ChunkingService
from app.services.ai_service import AIService
from app.rendering.markdown_renderer import MarkdownRenderer
from app.services.export_service import ExportService
from app.models.enums import ProcessingStatus

class PipelineService:

    def __init__(self):

        self.extraction = ExtractionService()
        self.processing = DocumentProcessor()
        self.chunking = ChunkingService()
        self.ai = AIService()
        self.renderer = MarkdownRenderer()
        self.exporter = ExportService()

    def process(self, collection):
        collection = self.extraction.process(collection)
        collection = self.processing.process(collection)

        generated_sections = []

        for source in collection.sources:
            if (not source.raw_content
                or len(source.raw_content.strip()) < 200
            ):
                source.status = ProcessingStatus.FAILED
                source.error = "No extractable text found."

                print(f"Skipping {source.title}: no usable text extracted.")

                continue

            chunks = self.chunking.process(source)

            if not chunks:
                generated_sections.append(f"## {source.title}\n\nNo content was available to chunk from this file.")
                continue

            try:
                outline = self.ai.generate_outline(chunks)
                print(f"--- OUTLINE FOR {source.title} ---")
                print(outline)
                print("-----------------------------------")
                generated = self.ai.generate_from_chunks(chunks, outline)
                generated_sections.extend(generated)
            except Exception as exc:
                generated_sections.append(f"## {source.title}\n\nAI generation failed: {exc}")

        if not generated_sections:
            fallback_text = "\n\n".join(
                f"## {source.title}\n\n{source.raw_content[:4000]}"
                for source in collection.sources
                if source.raw_content
            )
            merged_document = fallback_text or "No content could be generated from the provided input."
        else:
            try:
                merged_document = self.ai.merge_sections(generated_sections)
                print("\n========== MERGE STATS ==========")
                print(f"Characters: {len(merged_document)}")
                print(f"Words: {len(merged_document.split())}")
                print("=================================\n")
            except Exception as exc:
                merged_document = "\n\n".join(generated_sections)
                print(f"Merge failed: {exc}")

        markdown = self.renderer.render([merged_document])
        output_file = self.exporter.export(markdown, "notes")

        return output_file

