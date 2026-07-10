from dataclasses import dataclass, field


@dataclass
class KnowledgeBlock:
    type: str
    content: str


@dataclass
class KnowledgeSection:
    title: str
    blocks: list[KnowledgeBlock] = field(default_factory=list)


@dataclass
class KnowledgeDocument:
    title: str = ""
    sections: list[KnowledgeSection] = field(default_factory=list)