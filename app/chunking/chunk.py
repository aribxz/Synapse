from dataclasses import dataclass


@dataclass
class Chunk:
    id: int
    text: str
    estimated_tokens: int