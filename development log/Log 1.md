Architecture (Current) High-level flow:

```
User Input (URL / File)
        ↓
Flask Route
        ↓
Controller (planned)
        ↓
ExtractionService (NEW - central orchestrator)
        ↓
InputRouter
        ↓
Extractor Registry
        ↓
Specific Extractor (PDF / YouTube / etc.)
        ↓
KnowledgeSource.raw_content populated
        ↓
KnowledgeCollection updated
```

📦 Core Data Models KnowledgeSource Represents a single input item. Fields:

- `id` (UUID)
    
- `source_type` (Enum: PDF, YOUTUBE, DOCX, PPTX, WEBPAGE, TXT)
    
- `title`
    
- `raw_content` (extracted text)
    
- `metadata` (dict: path, url, video_id, etc.)
    
- `status` (ProcessingStatus enum)
    
- `error` KnowledgeCollection Represents a full user session. Fields:
    
- `id` (UUID)
    
- `sources` (List[KnowledgeSource])
    
- `topic`
    
- `status`
    
- `created_at` Enums
    
- `SourceType` → defines input type
    
- `ProcessingStatus` → PENDING, EXTRACTING, EXTRACTED, FAILED, etc. 🔧 Ingestion Layer (IMPLEMENTED) InputRouter
    
- Takes a `KnowledgeSource`
    
- Uses `ExtractorRegistry`
    
- Returns appropriate extractor result ExtractorRegistry Maps:
    

```
PDF → PDFExtractor
DOCX → DocxExtractor
PPTX → PPTXExtractor
YOUTUBE → YouTubeExtractor
WEBPAGE → WebExtractor
```

Extractors Implemented PDFExtractor

- Uses `PyMuPDF (fitz)`
    
- Extracts page text DocxExtractor
    
- Uses `python-docx`
    
- Joins paragraph text PPTXExtractor
    
- Uses `python-pptx`
    
- Extracts shape text (basic) WebExtractor
    
- Uses `trafilatura`
    
- Fetches and cleans HTML text YouTubeExtractor
    
- Uses `youtube-transcript-api`
    
- Extracts transcript text via video_id ⚙️ Service Layer (NEW) ExtractionService (IMPLEMENTED) Responsibilities:
    
- Iterates over KnowledgeCollection.sources
    
- Calls InputRouter per source
    
- Updates:
    
    - `raw_content`
    - `status`
    - `error handling` Features:
- Per-source failure isolation
    
- Status tracking (EXTRACTING → EXTRACTED / FAILED) 🧠 Design Principles
    
- Service-oriented architecture (controllers are thin)
    
- Registry pattern for extensibility
    
- Enum-based type safety
    
- Dataclasses for structured models
    
- One-way pipeline: input → extraction → future preprocessing → LLM → markdown
    
- No DB, no auth, no persistence (V1 scope) 🚫 Explicitly NOT in V1
    
- No user accounts
    
- No database
    
- No vector DB / RAG
    
- No chat interface
    
- No flashcards / quiz system
    
- No Obsidian sync
    
- No OCR pipeline (for now) 📌 Current Status Completed:
    
- Flask app setup
    
- App factory pattern
    
- Folder architecture
    
- Domain models
    
- Extractors (all implemented)
    
- Registry system
    
- Input router
    
- ExtractionService (core orchestration) Next Step:
    
- Wire ExtractionService into Controller
    
- Build Input Controller
    
- Create end-to-end test pipeline (file → output)