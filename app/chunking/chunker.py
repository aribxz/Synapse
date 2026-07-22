from app.chunking.chunk import Chunk


class Chunker:

    def __init__(self, max_tokens: int = 1200):
        self.max_tokens = max_tokens

    def chunk(self, text: str) -> list[Chunk]:
        words = text.split()
        chunks = []
        current_words = []
        current_tokens = 0
        chunk_id = 1

        for word in words:
            estimated = len(word) // 4 + 1

            if current_tokens + estimated > self.max_tokens:
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        text=" ".join(current_words),
                        estimated_tokens=current_tokens
                    )
                )
                chunk_id += 1
                current_words = []
                current_tokens = 0

            current_words.append(word)
            current_tokens += estimated

        if current_words: # leftover words

            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=" ".join(current_words),
                    estimated_tokens=current_tokens
                )
            )
        print(f"Created {len(chunks)} chunks.", flush=True)

        for chunk in chunks:
            print(f"Chunk {chunk.id}: {chunk.estimated_tokens} estimated tokens", flush=True)
            
        return chunks