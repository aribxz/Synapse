from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from app.models.enums import ProcessingStatus
from app.models.knowledge_source import KnowledgeSource


@dataclass
class KnowledgeCollection:
    sources: list[KnowledgeSource] = field(default_factory=list)
    topic: str = ""
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid4()))