# Main filein Processing folder. It cleans the raw text, adds metadata and token estimation and gives it back to collection.

from app.processing.cleaners import TextCleaner
from app.processing.metadata import MetadataExtractor
from app.processing.token_estimator import TokenEstimator

class DocumentProcessor:
    def __init__(self):
        self.cleaner = TextCleaner()
        self.metadata = MetadataExtractor()
        self.token_estimator = TokenEstimator()
    
    def process(self, collection):
        for source in collection.sources:
            source.raw_content = self.cleaner.clean(source.raw_content)
            self.metadata.enrich(source)
            source.metadata["estimated_tokens"] = (self.token_estimator.estimate(source.raw_content))

        return collection