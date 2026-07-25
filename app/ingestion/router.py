# Main file in ingestion folder. It calls registry to know what type of extract to call and then gives the extracted text.

from app.ingestion.registry import ExtractorRegistry

class InputRouter:
    def __init__(self):
        self.registry = ExtractorRegistry()

    def route(self, source):
        extractor = self.registry.get(source.source_type)
        return extractor.extract(source)