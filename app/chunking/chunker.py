from app.chunking.chunk import Chunk


class Chunker:

    def __init__(self, max_tokens: int = 3000):
        self.max_tokens = max_tokens

    def chunk(self, text: str) -> list[Chunk]:
        words = text.split() # Turns the raw text into a giant list of individual words.

        chunks = []
        current_words = []
        current_tokens = 0
        chunk_id = 1

        for word in words:
            estimated = max(1, len(word) // 4) # Even tiny words like a and e have at least 1 cost.

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

        return chunks