from abc import ABC, abstractmethod

from app.models.knowledge_source import KnowledgeSource

class BaseExtractor(ABC):

    @abstractmethod
    def extract(self, source: KnowledgeSource) -> KnowledgeSource: # Return Type Annotation
        """extract test into source.raw_content"""
        pass
