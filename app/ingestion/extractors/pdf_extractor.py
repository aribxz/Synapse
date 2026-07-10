from pathlib import Path
import fitz

from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource

class PDFExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        pdf = fitz.open(source.metadata["path"])

        text = ""
        for page in pdf:
            text += str(page.get_text())

        source.raw_content = text
        return source