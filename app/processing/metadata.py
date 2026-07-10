class MetadataExtractor:
    def enrich(self, source):
        source.metadata["character_count"] = len(source.raw_content)
        source.metadata["word_count"] = len(source.raw_content.split()) # Cuts every space so only words are left and therfore word count.

        return source