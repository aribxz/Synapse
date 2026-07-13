# Codebase Dump

Total files included: 45

## File list
- .\app\__init__.py
- .\app\chunking\chunk.py
- .\app\chunking\chunker.py
- .\app\controllers\input_controller.py
- .\app\controllers\source_factory.py
- .\app\ingestion\base_extractor.py
- .\app\ingestion\extractors\docx_extractor.py
- .\app\ingestion\extractors\pdf_extractor.py
- .\app\ingestion\extractors\pptx_extractor.py
- .\app\ingestion\extractors\web_extractor.py
- .\app\ingestion\extractors\youtube_extractor.py
- .\app\ingestion\registry.py
- .\app\ingestion\router.py
- .\app\llm\client.py
- .\app\llm\extraction_parser.py
- .\app\llm\knowledge_models.py
- .\app\llm\models.py
- .\app\llm\outline_parser.py
- .\app\llm\prompt_builder.py
- .\app\llm\prompts\__init__.py
- .\app\llm\prompts\base.py
- .\app\llm\prompts\extraction.py
- .\app\llm\prompts\merge.py
- .\app\llm\prompts\outline.py
- .\app\llm\prompts\study_notes.py
- .\app\llm\prompts\teaching.py
- .\app\models\enums.py
- .\app\models\knowledge_collection.py
- .\app\models\knowledge_document.py
- .\app\models\knowledge_source.py
- .\app\processing\cleaners.py
- .\app\processing\document_processor.py
- .\app\processing\metadata.py
- .\app\processing\token_estimator.py
- .\app\rendering\markdown_renderer.py
- .\app\routes\main.py
- .\app\services\ai_service.py
- .\app\services\chunking_service.py
- .\app\services\export_service.py
- .\app\services\extraction_service.py
- .\app\services\pipeline_service.py
- .\app\templates\index.html
- .\config.py
- .\generate_dev_log.py
- .\run.py

---

--- FILE: .\app\__init__.py ---

```
# __init__.py file is a package.
from flask import Flask 

def create_app():
    app = Flask(__name__)

    from app.routes.main import main_bp  #Tells to look inside app, then routes for main file
    app.register_blueprint(main_bp)

    return app
```

--- FILE: .\app\chunking\chunk.py ---

```
from dataclasses import dataclass


@dataclass
class Chunk:
    id: int
    text: str
    estimated_tokens: int
```

--- FILE: .\app\chunking\chunker.py ---

```
from app.chunking.chunk import Chunk


class Chunker:

    def __init__(self, max_tokens: int = 3000):
        self.max_tokens = max_tokens

    def chunk(self, text: str) -> list[Chunk]:
        words = text.split() # Turns the raw text into a giant list of individual words.

        chunks = []
        current_words = []
        current_tokens = 0
        chunk_id = 1

        for word in words:
            estimated = max(1, len(word) // 4) # Even tiny words like a and e have at least 1 cost.

            if current_tokens + estimated > self.max_tokens:

                chunks.append(  
                    Chunk(
                        id=chunk_id,
                        text=" ".join(current_words),
                        estimated_tokens=current_tokens
                    )
                )

                chunk_id += 1
                current_words = []
                current_tokens = 0

            current_words.append(word)
            current_tokens += estimated

        if current_words: # leftover words

            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=" ".join(current_words),
                    estimated_tokens=current_tokens
                )
            )

        return chunks
```

--- FILE: .\app\controllers\input_controller.py ---

```
from app.models.enums import SourceType
from app.models.knowledge_collection import KnowledgeCollection
from app.models.knowledge_source import KnowledgeSource
from pathlib import Path
from werkzeug.utils import secure_filename

from app.controllers.source_factory import SourceFactory
from app.services.extraction_service import ExtractionService
from app.services.pipeline_service import PipelineService


class InputController:
    def __init__(self):
        self.pipeline = PipelineService()

    def process_request(self, request):
        collection = KnowledgeCollection()
        
        upload_folder = Path("uploads") # checks for a uploads folder if not creates it
        upload_folder.mkdir(exist_ok=True) # bypass if it already exists

        for file in request.files.getlist("files"):
            # getlist : I know there might be more than one item under this label, so please go ahead and gather all of them into a list for me.
            # request.files is a html attribute
            if file.filename == "": # if the user selected upload but there is no file
                continue

            filename = secure_filename(file.filename) # security check for / characters
            filepath = upload_folder / filename # Take this directory path and append this filename to it with the correct slash character
            file.save(filepath)

            source = SourceFactory.from_upload_file(file) #Source Factory allows it to know what format it is
            source.metadata["path"] = str(filepath)

            collection.sources.append(source) 

        urls = request.form.get("urls", "") # Grabs the text from the "urls" input box on your webpage

        for url in urls.splitlines():
            url = url.strip() # removes accidental spaces

            if not url:
                continue

            source = SourceFactory.from_url(url)
            source.metadata["url"] = url

            collection.sources.append(source)

        output = self.pipeline.process(collection)
        return output
```

--- FILE: .\app\controllers\source_factory.py ---

```
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
        
```

--- FILE: .\app\ingestion\base_extractor.py ---

```
from abc import ABC, abstractmethod

from app.models.knowledge_source import KnowledgeSource

class BaseExtractor(ABC):

    @abstractmethod
    def extract(self, source: KnowledgeSource) -> KnowledgeSource: # Return Type Annotation
        """extract test into source.raw_content"""
        pass

```

--- FILE: .\app\ingestion\extractors\docx_extractor.py ---

```
import docx

from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource

class DocxExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        doc = docx.Document(source.metadata["path"])

        full_text = [para.text for para in doc.paragraphs] 
        source.raw_content = "\n".join(full_text)
        return source
```

--- FILE: .\app\ingestion\extractors\pdf_extractor.py ---

```
from pathlib import Path
import fitz

from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource

class PDFExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        pdf = fitz.open(source.metadata["path"])

        text = ""
        for page in pdf:
            text += str(page.get_text())

        source.raw_content = text
        return source
```

--- FILE: .\app\ingestion\extractors\pptx_extractor.py ---

```
from pptx import Presentation

from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource

class PPTXExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        prs = Presentation(source.metadata["path"])

        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"): # "Hey, does this specific object even have a 'text' property?"
                    text.append(getattr(shape, "text"))

        source.raw_content = "\n".join(text)
        return source
```

--- FILE: .\app\ingestion\extractors\web_extractor.py ---

```
import trafilatura

from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource

class WebExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        url = source.metadata["url"]

        html = trafilatura.fetch_url(url)

        if html is None:
            raise ValueError(f"Failed to download content from URL : {url}")
        
        text = trafilatura.extract(html)

        if text is None:
            source.raw_content = ""

        else:
            source.raw_content = text
            
        return source
```

--- FILE: .\app\ingestion\extractors\youtube_extractor.py ---

```
from urllib.parse import parse_qs, urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource


def extract_video_id_from_url(url: str) -> str:
    parsed = urlparse(url) # Slices the url into structured segments 

    if parsed.netloc.endswith("youtu.be"): # netloc is the youtube.com part
        return parsed.path.lstrip("/") # removes / and returns the query

    if parsed.netloc and "youtube.com" in parsed.netloc: # if browser url
        query_params = parse_qs(parsed.query) # query -> removes the ? part from youtube.com and parse_qs -> converts text into clean python dictionary
        if "v" in query_params and query_params["v"]:  # Ex : "v": ["ZkBTTlH7bBU"] -> the unique id
            return query_params["v"][0] 

    return url


class YouTubeExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        video_id = extract_video_id_from_url(source.metadata["url"])

        yt_api = YouTubeTranscriptApi()
        transcript_data = yt_api.fetch(video_id)

        formatter = TextFormatter()
        clean_text = formatter.format_transcript(transcript_data)

        source.raw_content = clean_text.replace("\n", " ")

        return source
```

--- FILE: .\app\ingestion\registry.py ---

```
from app.models.enums import SourceType
from app.ingestion.extractors.pdf_extractor import PDFExtractor
from app.ingestion.extractors.docx_extractor import DocxExtractor
from app.ingestion.extractors.pptx_extractor import PPTXExtractor
from app.ingestion.extractors.youtube_extractor import YouTubeExtractor
from app.ingestion.extractors.web_extractor import WebExtractor

class ExtractorRegistry:
    def __init__(self):
        self.extractors = {
            SourceType.PDF: PDFExtractor(),
            SourceType.DOCX: DocxExtractor(),
            SourceType.PPTX: PPTXExtractor(),
            SourceType.YOUTUBE: YouTubeExtractor(),
            SourceType.WEBPAGE: WebExtractor()
        }

    def get(self, source_type):
        return self.extractors[source_type]
```

--- FILE: .\app\ingestion\router.py ---

```
from app.ingestion.registry import ExtractorRegistry

class InputRouter:
    def __init__(self):
        self.registry = ExtractorRegistry()

    def route(self, source):
        extractor = self.registry.get(source.source_type)
        return extractor.extract(source)
```

--- FILE: .\app\llm\client.py ---

```
import os

from groq import Groq
from dotenv import load_dotenv
from app.llm.models import LLMRequest, LLMResponse

load_dotenv()

class GroqClient:
    def __init__(self) -> None:
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def generate(self, request: LLMRequest, model="llama-3.3-70b-versatile"):
        response = self.client.chat.completions.create( # Initialises request and sends it to groq
            model=model, messages=[
                {
                    "role" : "system",  # Tells the Ai what it is.
                    "content" : request.system_prompt
                },
                {
                    "role" : "user",
                    "content" : request.user_prompt
                }
            ])
        
      
        raw_content = response.choices[0].message.content or ""  # We get huge data back from groq, choices is the list of possible replies, 
        return LLMResponse(raw_output=raw_content)               # message is the part that contains text and content extracts that text.
         
```

--- FILE: .\app\llm\extraction_parser.py ---

```
import json

from app.llm.knowledge_models import ExtractedKnowledge


class ExtractionParser:

    def parse(self, raw: str) -> ExtractedKnowledge:

        try:
            data = json.loads(raw)
            return ExtractedKnowledge(**data) # The double asterisks data take our newly created dictionary of keys and values, unwrap them, and match them up perfectly with the inputs expected by the ExtractedKnowledge folder.

        except Exception:
            return ExtractedKnowledge()
```

--- FILE: .\app\llm\knowledge_models.py ---

```
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
```

--- FILE: .\app\llm\models.py ---

```
from dataclasses import dataclass, field
from app.models.enums import SourceType
@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str


@dataclass
class LLMResponse:
    raw_output: str
    parsed_output: dict | None = None

@dataclass
class PromptContext:
    source_type: SourceType
    chunk_index: int
    total_chunk: int
    document_title: str | None = None

@dataclass
class OutlineSection: #internal planning document.
    title: str
    sumamry: str
    chunk_indices: list[int] = field(default_factory=list)

@dataclass
class Outline:
    sections: list[OutlineSection] = field(default_factory=list)
```

--- FILE: .\app\llm\outline_parser.py ---

```
# the parser gains a global map, allowing it to intelligently jump to the exact sections of the documents it needs
from dataclasses import dataclass

@dataclass
class OutlineTopic:
    title: str
    description: str
    role: str
    source_chunks: list[int]

class OutlineParser:
    def parse(self, outline: str) -> list[OutlineTopic]: # It takes a raw string (outline) and returns a list of OutlineTopic objects.
        topics = []
        current = {}

        for line in outline.splitlines(): # Splits the large input string by newline characters
            line = line.strip() # Removes whitespace from the start and end of the line

            if not line: 
                continue

            if line.startswith("Title:"):
                current["title"] = line.removeprefix("Title:").strip()  # removeprefix() crops away that header tag, .strip() scrubs any remaining dead space before the actual textual data
            
            elif line.startswith("Description:"):
                current["description"] = line.removeprefix("Description:").strip()

            elif line.startswith("Role:"):
                current["role"] = line.removeprefix("Role:").strip()

            elif line.startswith("Source Chunks:"):
                raw = line.removeprefix("Source Chunks:").strip()
                chunks = []

                for part in raw.split(","): # splits it wherever there is a comma.
                    part = part.strip() # breaks the text into individual pieces

                    if "-" in part:
                        start, end = map(int, part.split("-")) # Splits to find the starting point and the ending point.
                        chunks.extend(range(start, end + 1)) # Adds numbers in between (+1 cause python).

                    else:
                        chunks.append(int(part))
                
                current["source_chunks"] = chunks
                topics.append(OutlineTopic(**current))
                current = {}

        return topics



```

--- FILE: .\app\llm\prompt_builder.py ---

```
from app.llm.models import LLMRequest
from app.llm.prompts import STUDY_NOTES_PROMPT
from app.llm.prompts.outline import OUTLINE_PROMPT
from app.llm.prompts.merge import MERGE_PROMPT
from app.llm.outline_parser import OutlineTopic
from app.llm.prompts.teaching import TEACHING_PROMPT
from app.llm.prompts.extraction import EXTRACTION_PROMPT
from app.llm.knowledge_models import ExtractedKnowledge

import json
from dataclasses import asdict


class PromptBuilder:
    def _format_outline(self, outline: list[OutlineTopic]) -> str:
        """Helper method to turn our outline list into clean bullet points"""
        return "\n".join([f"- {topic.title} ({topic.role})" for topic in outline])

    def build_outline(self, chunks) -> LLMRequest:

        formatted_chunks = []

        for index, chunk in enumerate(chunks):
            formatted_chunks.append(
                                    f"""
                        ===== CHUNK {index + 1} =====

                        {chunk.text}
                        """
                                )

        combined_text = "\n".join(formatted_chunks)

        user_prompt = f"""
                        Analyze the following educational material.

                        Identify the major topics.

                        For every topic include:

                        - Title
                        - Description
                        - Role
                        - Source Chunk(s)

                        Material:

                        {combined_text}
                    """

        return LLMRequest(
            system_prompt=OUTLINE_PROMPT,
            user_prompt=user_prompt,
        )

    def build(
        self,
        text: str,
        outline: list[OutlineTopic],
        current_topic: OutlineTopic,
        topic_index: int,
        total_topics: int,
        previous_notes: str | None = None,
    ) -> LLMRequest:

        previous_section = previous_notes or "None (this is the first section)."

        outline_text = "\n".join(
            [
                f"- {topic.title} ({topic.role})"
                for topic in outline
            ]
        )

        user_prompt = f"""
                            DOCUMENT OUTLINE

                            {outline_text}

                            CURRENT TOPIC

                            Title:
                            {current_topic.title}

                            Description:
                            {current_topic.description}

                            Role:
                            {current_topic.role}

                            Topic {topic_index + 1} of {total_topics}

                            PREVIOUS SECTION

                            {previous_section}

                            YOUR RESPONSIBILITY

                            Write this section according to its role.

                            If the role is Motivation:
                            Explain why this topic exists before explaining how it works.

                            If the role is Intuition:
                            Help the reader build an intuitive mental model.

                            If the role is Mechanism:
                            Explain the complete process step-by-step.

                            If the role is Procedure:
                            Describe the algorithm or workflow clearly.

                            If the role is Example:
                            Focus on demonstrating the concept.

                            If the role is Edge Case:
                            Explain limitations, assumptions and special cases.

                            If the role is Takeaway:
                            Summarize the important lessons and connect them to earlier topics.

                            TASK

                            Using ONLY the source content below:

                            - Teach the material instead of summarizing it.
                            - Follow the document outline.
                            - Expand ideas when necessary.
                            - Explain the reasoning behind important steps.
                            - Define technical terms on first use.
                            - Avoid repeating previous sections.
                            - Assume this section will later be merged into one complete study guide.

                            SOURCE CONTENT

                            {text}
                        """

        return LLMRequest(
            system_prompt=STUDY_NOTES_PROMPT,
            user_prompt=user_prompt,
        )
    
    def build_merge(self, sections: list[str]) -> LLMRequest:
        combined = "\n\n".join(sections)

        user_prompt = f"""
                        Merge the following study guide sections into one polished document.

                        Study Guide Sections

                        {combined}
                    """

        return LLMRequest(
            system_prompt=MERGE_PROMPT,
            user_prompt=user_prompt,
        )
    
    def build_extraction(self, text: str) -> LLMRequest:

        return LLMRequest(
            system_prompt=EXTRACTION_PROMPT,
            user_prompt=text,
        )
    
    def build_teaching(
    self,
    knowledge: ExtractedKnowledge,
    outline: list[OutlineTopic],
    current_topic: OutlineTopic,
    previous_notes: str | None,
    topic_index: int,
    total_topics: int,
    ) -> LLMRequest:
        
        knowledge_json = json.dumps(
            asdict(knowledge),
            indent=2,
        )

        outline_text = self._format_outline(outline)

        previous = previous_notes or "None"

        user_prompt = f"""
                            DOCUMENT OUTLINE

                            {outline_text}

                            CURRENT TOPIC

                            Title: {current_topic.title}

                            Description: {current_topic.description}

                            Role: {current_topic.role}

                            PREVIOUS SECTION

                            {previous}

                            EXTRACTED KNOWLEDGE

                            {knowledge_json}
                         """

        return LLMRequest(
            system_prompt=TEACHING_PROMPT,
            user_prompt=user_prompt,
        )
```

--- FILE: .\app\llm\prompts\__init__.py ---

```
from .study_notes import STUDY_NOTES_PROMPT
from .outline import OUTLINE_PROMPT
from .merge import MERGE_PROMPT
from .extraction import EXTRACTION_PROMPT
from .teaching import TEACHING_PROMPT
```

--- FILE: .\app\llm\prompts\base.py ---

```
BASE_ROLE = """
You are an expert educator, technical writer, and instructional designer.

Your purpose is to transform educational material into accurate, well-structured learning resources.

General Rules:

- Base every statement only on the provided source material.
- Never invent facts, examples, or explanations that are not supported by the source.
- Preserve technical accuracy.
- Prioritize clarity over brevity.
- Use precise and consistent terminology.
- Write in professional technical English.
- Never produce conversational responses.
- Return only the requested output.
"""
```

--- FILE: .\app\llm\prompts\extraction.py ---

```
from .base import BASE_ROLE

EXTRACTION_PROMPT = f"""
{BASE_ROLE}

You are extracting knowledge from educational material.

Do NOT teach.

Do NOT summarize.

Do NOT format Markdown.

Extract every important piece of information into the following JSON structure.

{{
    "concepts": [],
    "definitions": [],
    "mechanisms": [],
    "algorithms": [],
    "examples": [],
    "formulas": [],
    "important_details": [],
    "pitfalls": [],
    "connections": []
}}

Rules

- Preserve every important technical fact.
- Never invent information.
- If a field has no content, return an empty list.
- Return ONLY valid JSON.
"""
```

--- FILE: .\app\llm\prompts\merge.py ---

```
from .base import BASE_ROLE

MERGE_PROMPT = f"""
{BASE_ROLE}

You are editing a completed technical study guide.

Several independently written sections have already been generated.

Your task is to combine them into one coherent document.

OBJECTIVES

- Preserve all important information.
- Remove duplicated explanations.
- Improve transitions between sections.
- Maintain a consistent heading hierarchy.
- Keep terminology consistent.
- Preserve technical accuracy.
- Do not shorten the document unless removing repetition.
- Do not invent new information.

OUTPUT

Return one polished Obsidian Markdown document.
"""
```

--- FILE: .\app\llm\prompts\outline.py ---

```
from .base import BASE_ROLE

OUTLINE_PROMPT = f"""
{BASE_ROLE}

You are planning a technical study guide.

Your job is NOT to teach.

Your job is to analyze the educational material and produce a writing plan for another AI.

For every major topic, produce exactly:

1. Title
2. Short Description (1-2 sentences)
3. Role (choose ONE)
   - Motivation
   - Intuition
   - Mechanism
   - Procedure
   - Example
   - Edge Case
   - Takeaway
4. Source Chunks (which chunk numbers this topic belongs to)

Rules:

- Preserve the logical flow of the source.
- Merge duplicate topics.
- Prefer fewer, larger sections over many tiny ones.
- Do not explain concepts in detail.
- Do not write study notes.
- Return only the outline.

Example:

Topic:
    Title: Proximity Matrix
    Description: Explains how Random Forest estimates similarity between samples.
    Role: Mechanism
    Source Chunks: 4-5
"""
```

--- FILE: .\app\llm\prompts\study_notes.py ---

```
from .base import BASE_ROLE

STUDY_NOTES_PROMPT = f"""
{BASE_ROLE}

You are writing ONE section of a larger study document.

The final document will be merged with other sections, so your output must integrate cleanly.

OBJECTIVE

Teach the material rather than summarize it.

The notes should read like a high-quality technical textbook written for university students.

GENERAL RULES

- Explain ideas completely.
- Preserve the instructor's reasoning.
- Preserve intuition whenever it appears.
- Never invent information.
- Build naturally on previous concepts.
- Avoid repeating definitions unnecessarily.

MARKDOWN STYLE

Use valid Obsidian Markdown.

Use this hierarchy consistently:

## Major Concept

Brief explanation.

### Why it Matters

Explain the motivation or purpose.

### How it Works

Explain the mechanism or process.

### Important Details

Include assumptions, caveats, limitations, formulas or implementation details when relevant.

### Example

Include an example only if the source provides one.

### Key Takeaways

- Bullet 1
- Bullet 2

FORMATTING RULES

- Prefer paragraphs over excessive bullet lists.
- Use numbered lists only for ordered procedures.
- Use bold only for important terminology.
- Never start with generic introductions.
- Never end with generic conclusions.
- Write only the current section.
"""
```

--- FILE: .\app\llm\prompts\teaching.py ---

```
from .base import BASE_ROLE

TEACHING_PROMPT = f"""
{BASE_ROLE}

You are writing one section of a university-level study guide.

You will receive structured knowledge extracted from the source.

Your task is to teach the material, not summarize it.

Rules

- Explain every important concept.
- Explain WHY before HOW whenever appropriate.
- Reorganize information into the clearest learning order.
- Use the supplied outline.
- Use the topic role.
- Preserve technical accuracy.
- Never invent facts.
- Infer explanations only when they are standard domain knowledge and clearly support understanding.
- Produce polished Obsidian Markdown.
"""
```

--- FILE: .\app\models\enums.py ---

```
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
```

--- FILE: .\app\models\knowledge_collection.py ---

```
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
```

--- FILE: .\app\models\knowledge_document.py ---

```
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
```

--- FILE: .\app\models\knowledge_source.py ---

```
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
```

--- FILE: .\app\processing\cleaners.py ---

```
import re # -> Regex (Regular Expressions)

class TextCleaner:
    def clean(self, text: str):
        text = text.replace("\r", "\n") # standardizes everything to \n
        text = re.sub(r"\n{3,}", "\n\n", text) # If you find 3 or more consecutive newlines in a row, shrink them down to a maximum of 2 newlines
        text = re.sub(r"[ \t]+", " ", text) # looks for any sequence of multiple spaces or tabs (\t) and collapses them down into a single, clean space
        text = text.strip() # Trims off any accidental trailing spaces or blank lines sitting at the very beginning or the very end of the entire document.

        return text

```

--- FILE: .\app\processing\document_processor.py ---

```
from app.processing.cleaners import TextCleaner
from app.processing.metadata import MetadataExtractor
from app.processing.token_estimator import TokenEstimator

class DocumentProcessor:
    def __init__(self):
        self.cleaner = TextCleaner()
        self.metadata = MetadataExtractor()
        self.token_estimator = TokenEstimator()
    
    def process(self, collection):
        for source in collection.sources:
            source.raw_content = self.cleaner.clean(source.raw_content)
            self.metadata.enrich(source)
            source.metadata["estimated_tokens"] = (self.token_estimator.estimate(source.raw_content))

        return collection
```

--- FILE: .\app\processing\metadata.py ---

```
class MetadataExtractor:
    def enrich(self, source):
        source.metadata["character_count"] = len(source.raw_content)
        source.metadata["word_count"] = len(source.raw_content.split()) # Cuts every space so only words are left and therfore word count.

        return source
```

--- FILE: .\app\processing\token_estimator.py ---

```
class TokenEstimator:
    def estimate(self, text):
        return len(text) // 4 # OpenAI's historical benchmark dictates that 1 token is roughly equal to 4 characters of English text.
```

--- FILE: .\app\rendering\markdown_renderer.py ---

```
class MarkdownRenderer:
    def render(self, markdown_sections):
        return "\n\n---\n\n".join(markdown_sections)
```

--- FILE: .\app\routes\main.py ---

```
from flask import Blueprint, render_template, request, send_file

from app.controllers.input_controller import InputController
from app.services.ai_service import AIService
from app.services.chunking_service import ChunkingService
from app.models.knowledge_source import KnowledgeSource
from app.models.enums import SourceType
from app.models.knowledge_collection import KnowledgeCollection
from app.services.extraction_service import ExtractionService

main_bp = Blueprint("main", __name__)
controller = InputController()

@main_bp.route("/")
def home():
    return render_template("index.html")

@main_bp.route("/process", methods=["POST"])
def process():
    print("--- Starting Processing Pipeline ---")
    output_file = controller.process_request(request)
    print(f"--- Extraction Finished, Processing sources ---")

    return send_file(
        output_file,
        as_attachment=True,
        download_name="notes.md"
    )

# @main_bp.route("/test-ai")
# def test_ai():
#     text = "Linear Regression is a supervised machine learning algorithm..."
#     ai = AIService()
#     try:
#         notes = ai.generate_from_chunks(text)
#         return f"<pre>{notes}</pre>"
#     except Exception as e:
#         # This will show you the exact error in your browser instead of crashing
#         return f"<h1>AI Error:</h1><pre>{str(e)}</pre>", 500
    

@main_bp.route("/test-chunk")
def test_chunk():

    source = KnowledgeSource(
        source_type=SourceType.PDF,
        title="Test PDF",
        metadata={
            "path": "test.pdf"
        }
    )

    collection = KnowledgeCollection([source])
    extraction = ExtractionService()
    collection = extraction.process(collection)

    chunk_service = ChunkingService()

    chunks = chunk_service.process(
        collection.sources[0]
    )

    return {
        "chunk_count": len(chunks),
        "sizes": [
            chunk.estimated_tokens
            for chunk in chunks
        ]
    }


```

--- FILE: .\app\services\ai_service.py ---

```
from app.llm.client import GroqClient
from app.llm.prompt_builder import PromptBuilder
from app.llm.outline_parser import OutlineParser
from app.llm.extraction_parser import ExtractionParser

class AIService:
    def __init__(self):
        self.client = GroqClient()
        self.prompt_builder = PromptBuilder()

    def generate_from_chunks(self, chunks, outline):
        outputs = []
        previous_notes = None
        total_topics = len(outline)

        for topic_index, topic in enumerate(outline):
            source_text = self._collect_topic_text(topic, chunks)

            try:
                extraction_request = self.prompt_builder.build_extraction(source_text)
                raw_json = self.client.generate(extraction_request).raw_output

                knowledge = ExtractionParser().parse(raw_json)

                teaching_request = self.prompt_builder.build_teaching(
                    knowledge=knowledge,
                    outline=outline,
                    current_topic=topic,
                    previous_notes=previous_notes,
                    topic_index=topic_index,
                    total_topics=total_topics,
                )

                response = self.client.generate(teaching_request)

                outputs.append(response.raw_output)
                previous_notes = response.raw_output

            except Exception as e:
                print(f"Generation failed: {e}")
                continue

        return outputs
    
    def generate_outline(self, chunks):
        request = self.prompt_builder.build_outline(chunks)
        response = self.client.generate(request)
        return OutlineParser().parse(response.raw_output)
    
    def merge_sections(self, sections):
        request = self.prompt_builder.build_merge(sections)
        response = self.client.generate(request)
        return response.raw_output
    
    def _collect_topic_text(self, topic, chunks):
        selected = []

        for index in topic.source_chunks:
            if 1 <= index <= len(chunks):
                selected.append(chunks[index - 1].text)

        return "\n\n".join(selected)
```

--- FILE: .\app\services\chunking_service.py ---

```
from app.chunking.chunker import Chunker


class ChunkingService:
    def __init__(self, chunker: Chunker | None = None):
        self.chunker = chunker or Chunker()

    def process(self, source):
        return self.chunker.chunk(source.raw_content)
```

--- FILE: .\app\services\export_service.py ---

```
from pathlib import Path

class ExportService:
    def export(self, markdown, filename):
        base_dir = Path(__file__).resolve().parent.parent

        output_dir = base_dir / "outputs"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"{filename}.md"

        output_file.write_text(markdown, encoding="utf-8") # This is the save

        return output_file
```

--- FILE: .\app\services\extraction_service.py ---

```
from app.ingestion.router import InputRouter
from app.models.enums import ProcessingStatus

class ExtractionService:
    def __init__(self):
        self.router = InputRouter()

    def process(self, collection):
        for source in collection.sources:
            try:
                source.status = ProcessingStatus.EXTRACTING
                updated_source = self.router.route(source) # Calls the correct extractor (like your PDF or YouTube tool), tears open the file, pulls out the clean text, stamps it complete, and hands back a newly updated envelope.
                
                source.raw_content = updated_source.raw_content # takes the freshly extracted text out of that returned object and saves it right back into our original source item
                source.status = ProcessingStatus.EXTRACTED

            except Exception as e:
                source.status = ProcessingStatus.FAILED
                source.error = str(e)
        
        return collection
```

--- FILE: .\app\services\pipeline_service.py ---

```
from app.services.extraction_service import ExtractionService
from app.processing.document_processor import DocumentProcessor
from app.services.chunking_service import ChunkingService
from app.services.ai_service import AIService
from app.rendering.markdown_renderer import MarkdownRenderer
from app.services.export_service import ExportService

class PipelineService:

    def __init__(self):

        self.extraction = ExtractionService()
        self.processing = DocumentProcessor()
        self.chunking = ChunkingService()
        self.ai = AIService()
        self.renderer = MarkdownRenderer()
        self.exporter = ExportService()

    def process(self, collection):
        collection = self.extraction.process(collection)
        collection = self.processing.process(collection)

        generated_sections = []

        for source in collection.sources:
            if not source.raw_content or not source.raw_content.strip():
                generated_sections.append(f"## {source.title}\n\nNo extractable text was found in this file.")
                continue

            chunks = self.chunking.process(source)

            if not chunks:
                generated_sections.append(f"## {source.title}\n\nNo content was available to chunk from this file.")
                continue

            try:
                outline = self.ai.generate_outline(chunks)
                print(f"--- OUTLINE FOR {source.title} ---")
                print(outline)
                print("-----------------------------------")
                generated = self.ai.generate_from_chunks(chunks, outline)
                generated_sections.extend(generated)
            except Exception as exc:
                generated_sections.append(f"## {source.title}\n\nAI generation failed: {exc}")

        if not generated_sections:
            raise RuntimeError(
                    "No sections were generated. AI generation failed."
                )
        else:
            merged_document = self.ai.merge_sections(generated_sections)

        markdown = self.renderer.render([merged_document])
        output_file = self.exporter.export(markdown, "notes")

        return output_file


```

--- FILE: .\app\templates\index.html ---

```
<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Pipeline Test</title>
</head>
<body>

<h1>Backend Integration Test</h1>

<form action="/process" method="POST" enctype="multipart/form-data">

    <input type="file" name="files" multiple>

    <br><br>

    <textarea
        name="urls"
        rows="8"
        cols="80"
        placeholder="One URL per line"
    ></textarea>

    <br><br>

    <button type="submit">
        Generate Notes
    </button>

</form>

</body>
</html>
```

--- FILE: .\config.py ---

```
# Config is the office
import os  # Bridge between os and computer system.

class config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key") 
```

--- FILE: .\generate_dev_log.py ---

```
import subprocess
import ollama
import datetime
import os

def get_git_changes():
    try:
        # Runs 'git diff HEAD' to see what changed compared to your last commit
        result = subprocess.run(
            ["git", "diff", "HEAD"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return "Error: Local Git tracking is not initialized or running properly."

def generate_markdown_summary(diff_text, day_num, phase_info, hours_worked):
    if not diff_text.strip():
        return "No changes detected since your last local commit point."
    
    current_date = datetime.date.today().strftime("%B %d, %Y")
    
    prompt = f"""
    You are an elite software engineering/machine learning mentor reviewing your student's daily work. 
    Analyze the provided local Git Diff changes and write a highly personalized, encouraging, 
    and deeply analytical development log in Markdown.

    Use this metadata at the very top:
    - Day: {day_num}
    - Phase: {phase_info}
    - Hours Worked: {hours_worked} hours
    - Date: {current_date}

    Follow this exact structural layout strictly:
    1. Title block matching the metadata format provided.
    2. 'What happened today, in one sentence?' (Make it punchy and impactful).
    3. 'The big problem you solved today:' (Frame the technical hurdle they overcame based on the code changes).
    4. 'The New Analogy:' (Create a clever, fitting real-world analogy like cooking, building, or assembly lines to explain the new architecture).
    5. 'What changed — file by file:' (List the specific files modified in the diff, marking new ones as [NEW] and altered ones as [Modified]. Explain what fields or logic changed).
    6. 'OOP / Code Concepts Introduced Today:' (A markdown table outlining patterns or syntax used in the diff).
    7. 'My opinion on Day {day_num}:' (Write an honest, insightful code review as a proud mentor. Include sections for 'What is going really well', 'Where to be careful now' regarding performance/edge-cases, and a 'Verdict' score).

    Make sure these are all well formatted and include good diagrams. The Architecture specifically should be well explained.
    Git Diff Data to Analyze:
    {diff_text}
    """
    
    # We use the specific Qwen model tag you just downloaded
    response = ollama.generate(model="qwen2.5-coder:7b-instruct-q4_K_M", prompt=prompt)
    return response["response"]

def main():
    print("--- End of Day Log Generator ---")
    day_num = input("What Day number is this? (e.g., 4): ")
    phase_info = input("What is the current Phase? (e.g., Part 3 — Intelligence Engine): ")
    hours_worked = input("How many hours did you work today? (e.g., ~3): ")
    
    print("\nReading local file changes...")
    changes = get_git_changes()
    
    print("Analyzing changes and generating your mentor-level markdown log...")
    markdown_log = generate_markdown_summary(changes, day_num, phase_info, hours_worked)
    
    # 1. Create the logs directory path string
    logs_folder = "logs"
    
    # 2. Automatically create the directory if it doesn't exist yet
    os.makedirs(logs_folder, exist_ok=True)
    
    # 3. Build the clean, custom filename requested
    filename = f"Day {day_num}.md"
    
    # 4. Safely join the folder path and filename together
    file_path = os.path.join(logs_folder, filename)
    
    # 5. Write the file into the logs folder
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_log)
    
    print(f"\nSuccess! '{filename}' has been saved inside the '{logs_folder}' folder.")

if __name__ == "__main__":
    main()
```

--- FILE: .\run.py ---

```
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

```

