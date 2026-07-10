from app.services.extraction_service import ExtractionService
from app.processing.document_processor import DocumentProcessor
from app.services.chunking_service import ChunkingService
from app.services.ai_service import AIService
from app.rendering.markdown_renderer import MarkdownRenderer
from app.services.export_service import ExportService

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
            if not source.raw_content or not source.raw_content.strip():
                generated_sections.append(f"## {source.title}\n\nNo extractable text was found in this file.")
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
            raise RuntimeError(
                    "No sections were generated. AI generation failed."
                )
        else:
            merged_document = self.ai.merge_sections(generated_sections)

        markdown = self.renderer.render([merged_document])
        output_file = self.exporter.export(markdown, "notes")

        return output_file

