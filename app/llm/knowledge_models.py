from dataclasses import dataclass, field


@dataclass
class ExtractedKnowledge:

    concepts: list[str] = field(default_factory=list)

    definitions: list[str] = field(default_factory=list)

    mechanisms: list[str] = field(default_factory=list)

    algorithms: list[str] = field(default_factory=list)

    reasoning: list[str] = field(default_factory=list)

    intuition: list[str] = field(default_factory=list)

    why_it_matters: list[str] = field(default_factory=list)

    examples: list[str] = field(default_factory=list)

    important_details: list[str] = field(default_factory=list)

    common_misconceptions: list[str] = field(default_factory=list)

    prerequisites: list[str] = field(default_factory=list)

    connections: list[str] = field(default_factory=list)

    formulas: list[str] = field(default_factory=list)

    pitfalls: list[str] = field(default_factory=list)

    summary: str = ""

    coverage: str = "adequate"