from abc import ABC, abstractmethod # Abtactor base class forces a function to pass something otherwise it throws an error.

from app.models.knowledge_source import KnowledgeSource

class BaseExtractor(ABC):

    @abstractmethod
    def extract(self, source: KnowledgeSource) -> KnowledgeSource: # Return Type Annotation
        """extract test into source.raw_content"""
        pass 
