# Architecture Flow

```mermaid
graph TB
    subgraph User["User Layer"]
        A["Browser (index.html)"]
        B["Upload Files / Submit URLs"]
    end

    subgraph Web["Flask Web Layer"]
        C["run.py<br/>Entry Point"]
        D["app/__init__.py<br/>App Factory"]
        E["routes/main.py<br/>GET / POST /process"]
    end

    subgraph Controller["Controller Layer"]
        F["controllers/input_controller.py<br/>Parses request, creates KnowledgeCollection"]
        G["controllers/source_factory.py<br/>Factory: maps inputs → KnowledgeSource"]
    end

    subgraph Models["Data Models"]
        H["models/enums.py<br/>SourceType, ProcessingStatus, BlockType"]
        I["models/knowledge_source.py<br/>KnowledgeSource (dataclass)"]
        J["models/knowledge_collection.py<br/>KnowledgeCollection (dataclass)"]
        K["models/knowledge_document.py<br/>KnowledgeBlock, Section, Document"]
    end

    subgraph Pipeline["Pipeline (Facade)"]
        L["services/pipeline_service.py<br/>Orchestrates 6 subsystems sequentially"]
    end

    subgraph Extraction["Extraction Subsystem"]
        M["services/extraction_service.py<br/>Coordinates extraction"]
        N["ingestion/router.py<br/>Routes to correct extractor"]
        O["ingestion/registry.py<br/>Maps SourceType → Extractor"]
        P["ingestion/base_extractor.py<br/>ABC: abstract base extractor"]
        Q["ingestion/extractors/pdf_extractor.py<br/>PyMuPDF"]
        R["ingestion/extractors/docx_extractor.py<br/>python-docx"]
        S["ingestion/extractors/pptx_extractor.py<br/>python-pptx"]
        T["ingestion/extractors/web_extractor.py<br/>trafilatura"]
        U["ingestion/extractors/youtube_extractor.py<br/>youtube-transcript-api"]
    end

    subgraph Processing["Processing Subsystem"]
        V["processing/document_processor.py<br/>Clean, enrich, estimate tokens"]
        V1["processing/cleaners.py<br/>TextCleaner"]
        V2["processing/metadata.py<br/>MetadataExtractor"]
        V3["processing/token_estimator.py<br/>~4 chars/token"]
    end

    subgraph Chunking["Chunking Subsystem"]
        W["services/chunking_service.py<br/>Delegates to Chunker"]
        W1["chunking/chunk.py<br/>Chunk dataclass"]
        W2["chunking/chunker.py<br/>Sliding window, max 3000 tokens"]
    end

    subgraph AI["AI Generation Subsystem (2-Pass)"]
        X["services/ai_service.py<br/>Orchestrates outline → extract → teach → merge"]
        Y["llm/client.py<br/>GroqClient (llama-3.3-70b-versatile)"]
        Z["llm/prompt_builder.py<br/>Builds structured prompts"]
        AA["llm/outline_parser.py<br/>Parses outline → OutlineTopic[]"]
        AB["llm/extraction_parser.py<br/>Parses JSON → ExtractedKnowledge"]
        AC["llm/prompts/base.py<br/>Expert educator persona"]
        AD["llm/prompts/outline.py<br/>Topic planning prompt"]
        AE["llm/prompts/extraction.py<br/>JSON knowledge extraction prompt"]
        AF["llm/prompts/teaching.py<br/>Section writing prompt (teach)"]
        AG["llm/prompts/merge.py<br/>Document merge prompt"]
    end

    subgraph Rendering["Rendering & Export"]
        AH["rendering/markdown_renderer.py<br/>Joins sections with --- separator"]
        AI["services/export_service.py<br/>Writes app/outputs/notes.md"]
    end

    A -->|POST /process| E
    B -->|files + URLs| F
    E --> F
    F --> G
    G -->|SourceFactory| I
    I --> J
    J -->|KnowledgeCollection| L
    L -->|1. Extract| M
    M --> N
    N --> O
    O -->|SourceType| P
    P -->|PDF| Q
    P -->|DOCX| R
    P -->|PPTX| S
    P -->|Webpage| T
    P -->|YouTube| U
    Q & R & S & T & U -->|raw_content| I
    L -->|2. Clean| V
    V --> V1
    V --> V2
    V --> V3
    L -->|3. Chunk| W
    W --> W1
    W --> W2
    L -->|4. AI Generate| X
    X -->|build_outline| Z
    Z -->|OUTLINE_PROMPT| Y
    Y --> AA
    X -->|build_extraction| Z
    Z -->|EXTRACTION_PROMPT| Y
    Y --> AB
    X -->|build_teaching| Z
    Z -->|TEACHING_PROMPT| Y
    X -->|build_merge| Z
    Z -->|MERGE_PROMPT| Y
    AC --> AD & AE & AF & AG
    L -->|5. Render| AH
    L -->|6. Export| AI
    AI -->|notes.md| E
    E -->|send_file| A
```

---

## Data Flow Sequence

```mermaid
sequenceDiagram
    participant User as User Browser
    participant Route as routes/main.py
    participant Ctrl as input_controller.py
    participant Pipe as pipeline_service.py
    participant Extract as extraction_service.py
    participant Process as document_processor.py
    participant Chunk as chunking_service.py
    participant AI as ai_service.py
    participant Groq as Groq API
    participant Render as markdown_renderer.py
    participant Export as export_service.py

    User->>Route: POST /process (files + URLs)
    Route->>Ctrl: process_request(request)
    Ctrl->>Ctrl: Create KnowledgeCollection<br/>via SourceFactory
    Ctrl->>Pipe: process(collection)

    Note over Pipe: Step 1: Extract
    Pipe->>Extract: process(collection)
    Extract->>Extract: Route source → Extractor
    Extract-->>Pipe: raw_content populated

    Note over Pipe: Step 2: Clean & Enrich
    Pipe->>Process: process(collection)
    Process-->>Pipe: clean text, metadata

    Note over Pipe: Step 3: Chunk
    Pipe->>Chunk: process(source)
    Chunk-->>Pipe: list[Chunk]

    Note over Pipe: Step 4: AI Generation
    Pipe->>AI: generate_outline(chunks)
    AI->>Groq: OUTLINE_PROMPT
    Groq-->>AI: Outline response
    AI->>AI: Parse → OutlineTopic[]

    loop For each topic
        AI->>AI: Collect relevant chunks
        AI->>Groq: EXTRACTION_PROMPT
        Groq-->>AI: JSON knowledge
        AI->>AI: Parse → ExtractedKnowledge
        AI->>Groq: TEACHING_PROMPT
        Groq-->>AI: Section content
    end

    AI->>Groq: MERGE_PROMPT
    Groq-->>AI: Merged document
    AI-->>Pipe: merged markdown

    Note over Pipe: Step 5: Render
    Pipe->>Render: render([merged])
    Render-->>Pipe: formatted markdown

    Note over Pipe: Step 6: Export
    Pipe->>Export: export(md, "notes")
    Export-->>Pipe: output file path

    Pipe-->>Ctrl: output path
    Ctrl-->>Route: output path
    Route-->>User: send_file(notes.md)
```

---

## Class Hierarchy

```mermaid
classDiagram
    class BaseExtractor {
        <<abstract>>
        +extract(source) KnowledgeSource*
    }
    class PDFExtractor {
        +extract(source) KnowledgeSource
    }
    class DocxExtractor {
        +extract(source) KnowledgeSource
    }
    class PPTXExtractor {
        +extract(source) KnowledgeSource
    }
    class WebExtractor {
        +extract(source) KnowledgeSource
    }
    class YouTubeExtractor {
        +extract(source) KnowledgeSource
    }
    class ExtractorRegistry {
        +get(source_type) BaseExtractor
    }
    class InputRouter {
        +route(source) KnowledgeSource
    }
    class KnowledgeSource {
        +source_type: SourceType
        +title: str
        +raw_content: str
        +metadata: dict
        +status: ProcessingStatus
        +error: Optional[str]
        +id: str
    }
    class KnowledgeCollection {
        +sources: list~KnowledgeSource~
        +topic: str
        +status: ProcessingStatus
        +created_at: datetime
        +id: str
    }
    class Chunk {
        +id: int
        +text: str
        +estimated_tokens: int
    }
    class Chunker {
        +chunk(text) list~Chunk~
    }
    class ExtractedKnowledge {
        +concepts: list~str~
        +definitions: list~str~
        +mechanisms: list~str~
        +algorithms: list~str~
        +examples: list~str~
        +formulas: list~str~
        +important_details: list~str~
        +pitfalls: list~str~
        +connections: list~str~
    }
    class OutlineTopic {
        +title: str
        +description: str
        +role: str
        +source_chunks: list~int~
    }
    class GroqClient {
        +generate(request) LLMResponse
    }
    class PromptBuilder {
        +build_outline(chunks) LLMRequest
        +build_extraction(text) LLMRequest
        +build_teaching(knowledge, outline, ...) LLMRequest
        +build_merge(sections) LLMRequest
    }
    class PipelineService {
        +process(collection) str
    }
    class InputController {
        +process_request(request) str
    }
    class SourceFactory {
        +from_upload_file(file) KnowledgeSource
        +from_url(url) KnowledgeSource
    }

    BaseExtractor <|-- PDFExtractor
    BaseExtractor <|-- DocxExtractor
    BaseExtractor <|-- PPTXExtractor
    BaseExtractor <|-- WebExtractor
    BaseExtractor <|-- YouTubeExtractor
    ExtractorRegistry --> BaseExtractor : uses
    InputRouter --> ExtractorRegistry : uses
    InputController --> SourceFactory : uses
    InputController --> PipelineService : uses
    PipelineService --> Chunker : uses
    PipelineService --> GroqClient : uses
    PipelineService --> PromptBuilder : uses
    PipelineService --> KnowledgeSource : creates
    PipelineService --> KnowledgeCollection : processes
    Chunker --> Chunk : produces
    GroqClient --> ExtractedKnowledge : parses into
    GroqClient --> OutlineTopic : parses into
```

---

## Directory Tree

```text
📂 Hopeful, Ambition, Scared/
├── 📄 run.py                      # Entry point
├── 📄 config.py                   # Flask config
├── 📄 requirements.txt
├── 📄 .env                        # GROQ_API_KEY
├── 📂 app/
│   ├── 📄 __init__.py             # Flask app factory
│   ├── 📂 routes/
│   │   └── 📄 main.py             # GET /, POST /process
│   ├── 📂 controllers/
│   │   ├── 📄 input_controller.py
│   │   └── 📄 source_factory.py
│   ├── 📂 models/
│   │   ├── 📄 enums.py
│   │   ├── 📄 knowledge_source.py
│   │   ├── 📄 knowledge_collection.py
│   │   └── 📄 knowledge_document.py
│   ├── 📂 services/
│   │   ├── 📄 pipeline_service.py  # Facade
│   │   ├── 📄 extraction_service.py
│   │   ├── 📄 chunking_service.py
│   │   ├── 📄 ai_service.py
│   │   └── 📄 export_service.py
│   ├── 📂 ingestion/
│   │   ├── 📄 base_extractor.py    # ABC
│   │   ├── 📄 registry.py          # Registry pattern
│   │   ├── 📄 router.py            # Router pattern
│   │   └── 📂 extractors/
│   │       ├── 📄 pdf_extractor.py
│   │       ├── 📄 docx_extractor.py
│   │       ├── 📄 pptx_extractor.py
│   │       ├── 📄 web_extractor.py
│   │       └── 📄 youtube_extractor.py
│   ├── 📂 processing/
│   │   ├── 📄 document_processor.py
│   │   ├── 📄 cleaners.py
│   │   ├── 📄 metadata.py
│   │   └── 📄 token_estimator.py
│   ├── 📂 chunking/
│   │   ├── 📄 chunk.py
│   │   └── 📄 chunker.py
│   ├── 📂 llm/
│   │   ├── 📄 models.py
│   │   ├── 📄 knowledge_models.py
│   │   ├── 📄 client.py            # GroqClient
│   │   ├── 📄 prompt_builder.py
│   │   ├── 📄 outline_parser.py
│   │   ├── 📄 extraction_parser.py
│   │   └── 📂 prompts/
│   │       ├── 📄 base.py
│   │       ├── 📄 outline.py
│   │       ├── 📄 extraction.py
│   │       ├── 📄 teaching.py
│   │       └── 📄 merge.py
│   ├── 📂 rendering/
│   │   └── 📄 markdown_renderer.py
│   ├── 📂 templates/
│   │   └── 📄 index.html
│   └── 📂 outputs/
│       └── 📄 notes.md             # Generated output
├── 📂 tests/
├── 📂 uploads/
├── 📂 notes_test/
├── 📂 logs/
└── 📂 development log/
```
