from dataclasses import dataclass, field


@dataclass
class ExtractedKnowledge:
    concepts: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)
    mechanisms: list[str] = field(default_factory=list)
    algorithms: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    important_details: list[str] = field(default_factory=list)
    pitfalls: list[str] = field(default_factory=list)
    connections: list[str] = field(default_factory=list)