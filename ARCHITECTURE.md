# Application Architecture & Knowledge Processing Pipeline

## 📌 Overview

This document outlines the architectural layout and data orchestration flow of our Flask-based Intelligence Engine. The system uses a decoupled, modular design pattern to ingest external inputs (files, URLs), extract raw content, chunk it, run AI synthesis operations, and render a final compiled engineering log.

---

## 🏗️ Structural System Components

```text
📂 Root
├── 📄 run.py                          # Application Entry Point
└── 📂 app
    ├── 📄 __init__.py                 # Flask App Initialization
    ├── 📂 routes
    │   └── 📄 main.py                 # HTTP Endpoints & File Delivery
    ├── 📂 controllers
    │   └── 📄 input_controller.py     # Request Capture & Factory Isolation
    ├── 📂 ingestion
    │   └── 📄 router.py               # Extraction Route Mapping
    ├── 📂 services
    │   ├── 📄 pipeline_service.py     # Central Process Pipeline Coordinator
    │   ├── 📄 extraction_service.py   # Raw Content Data Extraction
    │   ├── 📄 chunking_service.py     # Text Segmentation & Context Controls
    │   ├── 📄 ai_service.py           # LLM Orchestration (Outlines & Generation)
    │   └── 📄 export_service.py       # IO Disk Operations & File Persist
    ├── 📂 processing
    │   └── 📄 document_processor.py   # Data Sanitization & Cleaning
    └── 📂 rendering
        └── 📄 markdown_renderer.py    # Token Stream Assembly
```

---

## 🔄 End-to-End Ingestion Pipeline Data Flow

The block diagram below tracks the lifetime of a transformation execution, showing how data mutates from an ephemeral user request into a physical asset on disk.

```text
[ User Interface ]
        │
        │ (Submit File / Link via index.html)
        ▼
[ app/routes/main.py ]  ◀────────────────────────────────────────┐
        │                                                         │
        │ 1. Route process() catches request                      │
        ▼                                                         │
[ app/controllers/input_controller.py ]                           │
        │                                                         │
        │ 2. Parses Payload -> Invokes SourceFactory              │
        │ 3. Instantiates KnowledgeSource & KnowledgeCollection   │
        ▼                                                         │
[ app/services/pipeline_service.py ]                              │
        │                                                         │
        │ 4. Orchestrates pipeline_service.process() sequential   │
        ├───► [ app/services/extraction_service.py ]              │
        │     Uses Ingestion Router to scrape URL / parse PDF     │
        │                                                         │
        ├───► [ app/processing/document_processor.py ]            │
        │     Sanitizes, strips artifacts, cleanses content       │
        │                                                         │
        ├───► [ app/services/chunking_service.py ]                │
        │     Segments raw context data into token-sized windows  │
        │                                                         │
        ├───► [ app/services/ai_service.py ]                      │
        │     • generate_outline()                                │
        │     • generate_from_chunks()                            │
        │     • merge_sections()                                  │
        │                                                         │
        └───► [ app/rendering/markdown_renderer.py ]              │
              Joins compiled strings into structurally sound MD   │
        │
        ▼
[ app/services/export_service.py ]
        │
        │ 5. Writes payload block directly to app/outputs/notes.md
        ▼
[ Local Disk Asset ] ───( Returns File Path )───► [ Flask send_file() ] ──┘
```

---

## 🛠️ Layered Responsibilities & Code Patterns

### 1. Request Handling Layer

- **`run.py` & `app/__init__.py`**
  - Configures global variables.
  - Establishes system context.
  - Spins up the Flask application runtime.

- **`app/routes/main.py`**
  - Thin routing layer.
  - Passes untrusted form data to the controller.
  - Serves generated files using Flask's `send_file()`.

- **`app/controllers/input_controller.py`**
  - Implements the **Factory Method Pattern**.
  - Parses incoming request parameters.
  - Uses `SourceFactory` to create `KnowledgeSource` objects.
  - Wraps them inside a unified `KnowledgeCollection`.

---

### 2. Coordination & Processing Layer

- **`app/services/pipeline_service.py`**
  - Implements the **Facade Pattern**.
  - Coordinates all subsystem execution.
  - Controls pipeline sequencing.
  - Prevents internal failures from propagating to the routing layer.

- **`app/services/extraction_service.py`**
  - Uses the internal `InputRouter`.
  - Detects source type.
  - Converts URLs, PDFs, documents, and other inputs into normalized text.

- **`app/services/chunking_service.py`**
  - Handles context window management.
  - Splits large documents into token-safe chunks.
  - Prevents exceeding LLM context limits.

---

### 3. Intelligence & Composition Layer

- **`app/services/ai_service.py`**
  - Coordinates the complete LLM workflow.
  - Builds document outlines (`generate_outline()`).
  - Generates section content (`generate_from_chunks()`).
  - Combines outputs using `merge_sections()`.

- **`app/rendering/markdown_renderer.py`**
  - Assembles structural components.
  - Normalizes spacing.
  - Produces clean Markdown output.

- **`app/services/export_service.py`**
  - Handles filesystem operations.
  - Safely writes generated files.
  - Returns the output path to the pipeline.

---

## 📈 Scalability Guidelines

### 1. Thread Concurrency

The modular design of `pipeline_service` allows extraction, processing, and generation modules to be executed as independent background tasks in the future, enabling parallel execution without blocking the primary Flask request thread.

### 2. Plugin Architecture

To support a new knowledge source:

1. Create a new parser under `app/ingestion/`.
2. Register it inside `app/ingestion/router.py`.
3. No changes are required in downstream pipeline orchestration, keeping the system open for extension while remaining closed for modification.

---

## ✅ Why This Structure Works

- **Directory Tree Added**
  - Presents the project hierarchy in a clear visual format for developers.

- **Platform-Independent Architecture Diagram**
  - Uses ASCII diagrams that render correctly on GitHub, VS Code, Obsidian, and Markdown viewers.

- **Separation of Concerns**
  - Each layer has a single, well-defined responsibility, making the codebase easier to understand and maintain.

- **Design Patterns**
  - Incorporates established software engineering principles:
    - Factory Method
    - Facade
    - Router
    - Service Layer

- **Scalability**
  - New extraction strategies and AI workflows can be added with minimal changes to existing code.

- **Maintainability**
  - Clear modular boundaries reduce coupling and simplify testing, debugging, and future feature development.