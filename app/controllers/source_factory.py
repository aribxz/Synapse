from pathlib import Path

from app.models.enums import SourceType
from app.models.knowledge_source import KnowledgeSource

class SourceFactory:
    
    @staticmethod
    def from_upload_file(file_storage):
        extension = Path(file_storage.filename).suffix.lower()

        source_map = {
            ".pdf": SourceType.PDF,
            ".docx": SourceType.DOCX,
            ".pptx": SourceType.PPTX,
            ".txt": SourceType.TXT,
        }

        if extension not in source_map:
            raise ValueError(f'Unsupported file type : {extension}')
        
        return KnowledgeSource(
            source_type = source_map[extension],
            title = file_storage.filename,
            metadata = {}
        )  
    
    @staticmethod
    def from_url(url):
        if "youtube.com" in url or "youtu.be" in url:
            source_type = SourceType.YOUTUBE

        else:
            source_type = SourceType.WEBPAGE

        return KnowledgeSource(
            source_type = source_type,
            title = url,
            metadata = {}
        )  
        