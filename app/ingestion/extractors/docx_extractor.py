import docx

from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource

class DocxExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        doc = docx.Document(source.metadata["path"])

        full_text = [para.text for para in doc.paragraphs] 
        source.raw_content = "\n".join(full_text)
        return source