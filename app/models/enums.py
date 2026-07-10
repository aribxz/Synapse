from enum import Enum # Names bound to a unique value.

class SourceType(Enum):
    YOUTUBE = "youtube"
    WEBPAGE = "webpage"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"

class ProcessingStatus(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    PREPROCESSED = "preprocessed"
    CHUNKED = "chunked"
    COMPLETED = "completed"
    FAILED = "failed"

class BlockType(Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    BULLETS = "bullets"
    CODE = "code"
    FORMULA = "formula"
    DIAGRAM = "diagram"
    WARNING = "warning"
    TIP = "tip"
    EXAMPLE = "example"
    TABLE = "table"
    QUOTE = "quote"