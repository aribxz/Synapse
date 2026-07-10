## Phase Overview

The project moved from building infrastructure to improving the intelligence of the note generation pipeline.

The main goal was to move from:

```
Transcript/PDF
        ↓
Chunk
        ↓
LLM Summary
        ↓
Markdown
```

towards:

```
Source Material
        ↓
Document Understanding
        ↓
Knowledge Extraction
        ↓
Teaching Generation
        ↓
Polished Markdown Notes
```

The focus shifted from "can the application process files?" to "can the application generate notes comparable to Claude?"

---

# Problem Identified

After testing a 3.5-hour Andrej Karpathy lecture and shorter StatQuest videos, the application successfully handled large inputs.

However, the generated notes had issues:

- Sections felt like independent summaries.
- The model followed transcript order too closely.
- Concepts were explained as facts rather than taught.
- Important reasoning and intuition were missing.
- Algorithms were sometimes split across chunks.
- Formatting consistency varied.

The root cause was identified:

The system was treating chunks as writing units.

The architecture was:

```
Chunk 1 → AI → Section 1

Chunk 2 → AI → Section 2

Chunk 3 → AI → Section 3
```

This caused:

- repeated introductions
- weak document flow
- loss of global context
- poor teaching structure

---

# Major Architectural Improvement 1

## Outline-Based Generation

Implemented a planning stage before writing.

New flow:

```
Document
    ↓
Outline Generation
    ↓
Topic Identification
    ↓
Section Generation
```

The outline became more than a list of topics.

Each topic now contains:

- Title
- Description
- Role
- Source chunk references

Example roles:

- Motivation
- Intuition
- Mechanism
- Procedure
- Example
- Edge Case
- Takeaway

Purpose:

Give every generated section a teaching responsibility instead of simply summarizing content.

---

# Major Architectural Improvement 2

## Topic-Based Generation Instead of Chunk-Based Generation

Previous:

```
Chunk
 ↓
Section
```

New:

```
Outline Topic
        ↓
Relevant Source Chunks
        ↓
Generated Section
```

The system now groups related chunks before generation.

Benefits:

- Algorithms remain together.
- Explanations are not cut in half.
- Examples stay connected to concepts.
- Sections represent actual learning units.

This was implemented inside AIService without changing the overall pipeline architecture.

---

# Major Architectural Improvement 3

## Extract → Teach Two-Pass Generation

A major weakness was that one LLM call was responsible for:

- understanding the source
- extracting facts
- deciding importance
- teaching
- formatting Markdown

This was separated.

New flow:

```
Topic Source Text

        ↓

Extraction Pass

        ↓

Structured Knowledge Object

        ↓

Teaching Pass

        ↓

Markdown Section
```

---

# Extraction Layer

Created an internal knowledge representation.

The extraction stage focuses only on preserving information.

Extracted categories:

- Concepts
- Definitions
- Mechanisms
- Algorithms
- Examples
- Formulas
- Important Details
- Pitfalls
- Connections

Important decision:

The JSON structure is internal only.

The user never sees it.

Its purpose is to prevent information loss before teaching.

---

# Teaching Layer

The teaching pass receives:

- extracted knowledge
- outline
- topic role
- previous section context

Its responsibility:

Transform information into educational Markdown.

Rules added:

- Explain concepts instead of summarizing.
- Explain why before how.
- Maintain technical accuracy.
- Create learner-friendly structure.
- Avoid unnecessary compression.

---

# Prompt Architecture Improvements

Separated prompts into specialized responsibilities:

Before:

```
One general prompt
```

After:

```
Base Role
    |
    ├── Outline Prompt
    |
    ├── Extraction Prompt
    |
    └── Teaching Prompt
```

This follows the single responsibility principle at the prompt level.

---

# Testing Results

Tested using:

- StatQuest Random Forest missing data video.

The output improved significantly.

Improvements observed:

## Better organization

The generated document had logical sections:

- Introduction
- Missing Data Handling
- Proximity Matrix
- Convergence
- Applications
- New Samples

instead of arbitrary chunk boundaries.

---

## Better continuity

The document no longer felt like separate AI summaries stitched together.

The flow became closer to a textbook chapter.

---

## Remaining Quality Issues

The output is improved but not yet Claude-level.

Remaining problems:

### 1. Explanation depth

The model explains:

"What happens"

better than:

"Why it happens"

Example:

It explains proximity matrices but does not always build intuition.

---

### 2. Missing mental models

Needs more:

- analogies
- intuition
- conceptual explanations

---

### 3. Generic examples

Examples are sometimes mentioned but not developed.

---

### 4. Still slightly transcript-driven

The model reorganizes better but still follows source order.

---

# Error Handling Improvement

A DOCX test revealed a product-level issue.

The Groq API hit its rate limit:

```
429 Rate Limit Exceeded
```

The AI generation failed.

However, the error message was passed into the merge stage as if it was valid content.

Problem:

```
AI Error
    ↓
Merge Pass
    ↓
Markdown Output
```

Fix:

Generation failures are now filtered out instead of becoming note content.

The system now handles external AI failures more safely.

---

# Current Architecture State

The pipeline remains:

```
InputController

↓

PipelineService

↓

ExtractionService

↓

DocumentProcessor

↓

ChunkingService

↓

AIService

        |
        ├── Outline Pass
        |
        ├── Extraction Pass
        |
        ├── Teaching Pass
        |
        └── Merge Pass

↓

MarkdownRenderer

↓

ExportService
```

Architecture is considered stable.

No more structural changes are planned.

---

# Current Status

Completed:

✅ Outline planning  
✅ Topic-based generation  
✅ Chunk grouping  
✅ Continuity handling  
✅ Extraction pass  
✅ Structured knowledge representation  
✅ Teaching pass  
✅ Improved error handling

Remaining:

1. Teaching prompt refinement
2. Few-shot example
3. Stronger merge editor
4. Markdown polish
5. Evaluation framework