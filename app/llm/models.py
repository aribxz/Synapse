from dataclasses import dataclass, field
from app.models.enums import SourceType

@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str
    max_tokens: int | None = None


@dataclass
class LLMResponse:
    raw_output: str
    parsed_output: dict | None = None
    usage: dict | None = None

@dataclass
class PromptContext:
    source_type: SourceType
    chunk_index: int
    total_chunk: int
    document_title: str | None = None

@dataclass
class OutlineSection: #internal planning document.
    title: str
    sumamry: str
    chunk_indices: list[int] = field(default_factory=list)

@dataclass
class Outline:
    sections: list[OutlineSection] = field(default_factory=list)