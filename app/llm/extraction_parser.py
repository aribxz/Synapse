import json

from app.llm.knowledge_models import ExtractedKnowledge


class ExtractionParser:

    def parse(self, raw: str) -> ExtractedKnowledge:

        try:
            data = json.loads(raw)
            return ExtractedKnowledge(**data) # The double asterisks data take our newly created dictionary of keys and values, unwrap them, and match them up perfectly with the inputs expected by the ExtractedKnowledge folder.

        except Exception:
            return ExtractedKnowledge()