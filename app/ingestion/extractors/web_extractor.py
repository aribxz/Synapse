import trafilatura

from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource

class WebExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        url = source.metadata["url"]

        html = trafilatura.fetch_url(url)

        if html is None:
            raise ValueError(f"Failed to download content from URL : {url}")
        
        text = trafilatura.extract(html)

        if text is None:
            source.raw_content = ""

        else:
            source.raw_content = text
            
        return source