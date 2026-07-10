from app.chunking.chunker import Chunker


class ChunkingService:
    def __init__(self, chunker: Chunker | None = None):
        self.chunker = chunker or Chunker()

    def process(self, source):
        return self.chunker.chunk(source.raw_content)