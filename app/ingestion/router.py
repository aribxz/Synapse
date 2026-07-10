from app.ingestion.registry import ExtractorRegistry

class InputRouter:
    def __init__(self):
        self.registry = ExtractorRegistry()

    def route(self, source):
        extractor = self.registry.get(source.source_type)
        return extractor.extract(source)