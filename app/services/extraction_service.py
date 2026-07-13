from app.ingestion.router import InputRouter
from app.models.enums import ProcessingStatus

class ExtractionService:
    def __init__(self):
        self.router = InputRouter()

    def process(self, collection):
        for source in collection.sources:
            try:
                source.status = ProcessingStatus.EXTRACTING
                updated_source = self.router.route(source) # Calls the correct extractor (like your PDF or YouTube tool), tears open the file, pulls out the clean text, stamps it complete, and hands back a newly updated envelope.
                
                source.raw_content = updated_source.raw_content # takes the freshly extracted text out of that returned object and saves it right back into our original source item

                if len(source.raw_content.strip()) < 200:
                    source.status = ProcessingStatus.FAILED
                    source.error = "No extractable text found."
                    continue

                source.status = ProcessingStatus.EXTRACTED

            except Exception as e:
                source.status = ProcessingStatus.FAILED
                source.error = str(e)
        
        return collection