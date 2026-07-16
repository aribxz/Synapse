from app.ingestion.base_extractor import BaseExtractor
from app.models.enums import SourceType


class TxtExtractor(BaseExtractor):
    def extract(self, source):
        with open(source.metadata["path"], "r", encoding="utf-8") as f:
            source.raw_content = f.read()
        return source