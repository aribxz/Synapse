# This contains the initial Knowledge object, basically if a user uploads 2 pdfs then 2 KnowledgeSource objects are intiated for each of them.

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from app.models.enums import ProcessingStatus, SourceType

@dataclass
class KnowledgeSource:
    source_type : SourceType
    title : str
    raw_content : str = ""
    metadata : dict = field(default_factory=dict) # "Don't give me a shared dictionary. Instead, run the dict() function to create a brand-new, empty dictionary for every single object I create."
    status : ProcessingStatus = ProcessingStatus.PENDING
    error : Optional[str] = None # tells python it could be a str or none
    id : str = field(default_factory=lambda : str(uuid4())) # generates a unique id