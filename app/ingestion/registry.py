from app.models.enums import SourceType
from app.ingestion.extractors.pdf_extractor import PDFExtractor
from app.ingestion.extractors.docx_extractor import DocxExtractor
from app.ingestion.extractors.pptx_extractor import PPTXExtractor
from app.ingestion.extractors.youtube_extractor import YouTubeExtractor
from app.ingestion.extractors.web_extractor import WebExtractor

class ExtractorRegistry:
    def __init__(self):
        self.extractors = {
            SourceType.PDF: PDFExtractor(),
            SourceType.DOCX: DocxExtractor(),
            SourceType.PPTX: PPTXExtractor(),
            SourceType.YOUTUBE: YouTubeExtractor(),
            SourceType.WEBPAGE: WebExtractor()
        }

    def get(self, source_type):
        return self.extractors[source_type]