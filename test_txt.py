import os
from app.ingestion.extractors.txt_extractor import TxtExtractor
from app.models.knowledge_source import KnowledgeSource
from app.models.enums import SourceType

source = KnowledgeSource(
    source_type=SourceType.TXT,
    title='test.txt',
    metadata={'path': 'C:/Users/ASUS/Downloads/Reinforcement Learning.txt'}
)

path = source.metadata['path']
print(f"File exists: {os.path.exists(path)}")
print(f"File size: {os.path.getsize(path) if os.path.exists(path) else 0}")

extractor = TxtExtractor()
result = extractor.extract(source)
content = result.raw_content
print(f"Extracted content length: {len(content) if content else 0}")
if content:
    print(f"First 200 chars: {content[:200]}")