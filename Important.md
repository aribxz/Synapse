| Field       | Why                                             |
| ----------- | ----------------------------------------------- |
| id          | Unique identifier                               |
| source_type | youtube / pdf / webpage / docx                  |
| title       | Display name                                    |
| raw_content | Extracted text                                  |
| metadata    | Flexible information like URL, filename, author |
| status      | pending, extracted, failed                      |
| error       | Error message if extraction fails               |
Browser

↓

Route

↓

Controller

↓

Service

↓

Model

# The Controller's Job

The controller should only:

- Receive the request.
- Validate basic inputs.
- Create a `KnowledgeCollection`.
- Pass it to the router.
- Return a response.

Browser

↓

Route

↓

Controller

↓

Router

↓

Extractor Registry

↓

Correct Extractor

↓

KnowledgeSource

↓

KnowledgeCollection

----
Input

↓

Router

↓

Registry

↓

Extractor Class

↓

Extractor

### Backend Pipeline

HTTP Request
      ↓
Flask Route
      ↓
KnowledgeSource
      ↓
KnowledgeCollection
      ↓
ExtractionService
      ↓
InputRouter
      ↓
Registry
      ↓
PDFExtractor
      ↓
PyMuPDF
      ↓
KnowledgeSource.raw_content
      ↓
Browser Response

### Change
POST /process

↓

Flask Route

↓

InputController.process_request(request)

↓

KnowledgeCollection

↓

ExtractionService

↓

Collection with extracted text

↓

(return for now)

### The Root Cause: The "Watchdog" Assassination

When you run Flask with `debug=True`, it uses a tool called `watchdog` to monitor your project folder. If it sees any file change, it automatically restarts the server so you don't have to restart it manually.

Here is exactly what just happened in a matter of milliseconds:

1. You visited `/test-ai`.
    
2. Your `GroqClient` woke up and prepared to make its very first internet request.
    
3. Behind the scenes, the Groq library relies on an HTTP library called `httpcore`. Because it was the first time using it, Python hastily created some internal cache files (or your antivirus/IDE briefly "touched" the files while scanning the new web request).
    
4. Flask's `watchdog` saw a file change inside your `.venv` folder.
    
5. **Flask panicked and instantly restarted the server.**
    
6. Because the server restarted _while_ it was talking to your browser, the connection was violently severed, resulting in the `ERR_CONNECTION_RESET (-101)` in Chrome.

### Pipeline
                   INPUT
                      │
      ┌───────────────┴────────────────┐
      │                                │
   Documents                         URLs
      │                                │
      └───────────────┬────────────────┘
                      │
              Source Factory
                      │
                      ▼
            KnowledgeCollection
                      │
                      ▼
            Pipeline Service
                      │
      ┌───────────────┼──────────────────┐
      │               │                  │
 Extraction     Processing         Chunking
      │               │                  │
      └───────────────┼──────────────────┘
                      ▼
               Prompt Builder
                      │
                      ▼
                 Groq Client
                      │
                      ▼
             Markdown Renderer
                      │
                      ▼
              Export Service
                      │
                      ▼
                Download notes.md


PipelineService
        │
        ▼
AIService
        │
        ├── Outline Pass
        │
        ├── For each topic
        │      │
        │      ├── Collect source chunks
        │      ├── Extract Pass
        │      ├── Parse JSON → ExtractedKnowledge
        │      ├── Teaching Pass
        │      └── Store section
        │
        └── Return sections