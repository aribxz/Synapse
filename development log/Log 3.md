# Development Report

**Development Phase:** Phase 3 – Note Generation Engine

**Focus:** Transition from infrastructure development to AI generation strategy

---

# Overview

Today's work marked one of the biggest conceptual shifts in the project since the introduction of `PipelineService`.

Up until now, nearly all development had focused on software engineering:

- application architecture
    
- service separation
    
- extraction pipeline
    
- chunking
    
- LLM integration
    
- rendering
    
- exporting
    

At the end of the previous phase, the application had reached an important milestone: it could successfully process real educational material end-to-end.

This included successfully processing a **3.5-hour Andrej Karpathy lecture**, demonstrating that the infrastructure was sufficiently robust for large inputs.

With infrastructure considered stable, the project's bottleneck shifted completely.

The problem was no longer _"Can the software process documents?"_

Instead, the question became:

> **"Can the software generate notes that genuinely rival Claude?"**

This realization fundamentally changed the direction of development.

---

# Evaluation of the Existing Generation Pipeline

The first step was evaluating the quality of the generated notes rather than the software itself.

Testing revealed several recurring weaknesses.

## 1. Notes were technically correct but overly compressed

The generated notes generally preserved factual correctness.

However, they often summarized concepts rather than teaching them.

Important reasoning, intuition, and explanatory flow from the instructor were frequently lost.

The notes resembled concise summaries rather than educational material.

---

## 2. Formatting lacked consistency

Although Markdown output worked correctly after removing the previous JSON generation stage, formatting varied between sections.

Different chunks naturally developed slightly different writing styles.

Heading structures were inconsistent.

Lists appeared in different formats.

Some concepts were explained while others were merely listed.

---

## 3. Long documents felt fragmented

This became the most significant architectural discovery.

Every chunk behaved like an independent document.

As a consequence:

- concepts were reintroduced repeatedly
    
- headings restarted unnecessarily
    
- terminology was defined multiple times
    
- transitions between sections felt artificial
    

The document no longer read like one coherent piece of writing.

Instead, it resembled several independent summaries concatenated together.

This issue became increasingly visible on longer lectures.

---

# Initial Attempt: Chunk Continuity

The first proposed solution involved introducing local continuity between chunks.

The idea was simple.

Instead of generating every chunk independently, each chunk would receive the notes generated from the previous chunk.

Conceptually:

```
Chunk 1
↓

Notes

↓

Chunk 2
+
Previous Notes

↓

Notes

↓

Chunk 3
+
Previous Notes
```

This approach attempted to mimic how a human author naturally remembers what has already been written.

---

# AIService Improvements

The existing `AIService` was modified conceptually.

Previously, every iteration simply generated notes.

```
for chunk:
    generate(chunk)
```

The new design introduced a `previous_notes` variable.

After each successful generation:

```
previous_notes = response.raw_output
```

The following chunk would receive those notes as additional context.

This represented the first attempt at preserving document continuity.

---

# Architectural Discussion

Although this approach improved local continuity, an important limitation became clear.

Passing the entire previous section increases prompt size continuously.

Large sections consume unnecessary context window space.

For long lectures, this would eventually become inefficient.

A possible optimization was discussed:

Instead of storing the entire previous section, store only a compressed continuity summary.

Example:

```
Covered:

• Motivation
• Attention
• Positional Encoding
```

This would dramatically reduce token usage while still preserving context.

However, this raised another concern.

Compression inevitably risks discarding information that later sections may rely upon.

Since preserving educational quality is the primary goal of StudyScore, this trade-off remained unresolved.

No implementation was performed at this stage.

---

# External Design Review

Rather than continuing to iterate solely through experimentation, an external architectural review was requested from Claude.

Instead of asking for prompt improvements, the request specifically focused on long-document generation strategies used in production-quality systems.

The resulting discussion significantly influenced the project's direction.

---

# Key Insight

The most important architectural insight from the review was the distinction between two different kinds of chunking.

## Input Chunking

Current chunking exists because LLMs have limited context windows.

Its purpose is purely technical.

It prevents extremely large lectures from exceeding model limits.

---

## Output Generation

The project had unintentionally allowed input chunks to dictate document structure.

One transcript chunk became one generated section.

This created an implicit one-to-one relationship:

```
Input Chunk

↓

Generated Section
```

The review highlighted that these are fundamentally different concerns.

Input chunking should remain an implementation detail.

Document structure should instead be determined by the educational content itself.

This became today's most important architectural realization.

---

# Shift Toward Outline-Driven Generation

Instead of generating notes immediately, the proposed future workflow introduces an intermediate planning stage.

Rather than:

```
Transcript

↓

Notes
```

the workflow becomes:

```
Transcript

↓

Outline

↓

Notes
```

The outline serves as a planning document rather than user-facing output.

Its purpose is to provide global awareness of the entire educational source before any detailed writing begins.

This mirrors the workflow used by human technical writers:

1. Understand the material.
    
2. Plan the document.
    
3. Write each section.
    
4. Perform a final edit.
    

This represents a significant philosophical shift in the AI generation strategy.

---

# Evaluation of the Proposed Pipeline

The proposed architecture consists of three conceptual stages.

## Outline Pass

Generate a concise document outline containing:

- major topics
    
- logical ordering
    
- brief descriptions
    

This stage is intentionally lightweight.

Its output is a planning artifact rather than study notes.

---

## Section Generation

Each section is generated independently using:

- the relevant source material
    
- the complete outline
    

This allows every generation call to understand the document's overall structure without repeatedly transmitting large amounts of generated text.

Unlike previous continuity approaches, this provides **global coherence** rather than merely local continuity.

---

## Merge Pass

Once every section has been generated, a final editing stage combines them into a single polished Markdown document.

Responsibilities include:

- removing duplicated explanations
    
- improving transitions
    
- unifying formatting
    
- maintaining consistent heading hierarchy
    

This stage focuses purely on editorial refinement rather than introducing new educational content.

---

# Architectural Decisions

Several important architectural decisions were made during today's discussions.

## 1. Existing software architecture remains unchanged.

The following components remain valid:

- InputController
    
- PipelineService
    
- ExtractionService
    
- DocumentProcessor
    
- ChunkingService
    
- MarkdownRenderer
    
- ExportService
    

Only the AI generation strategy evolves.

This preserves the modular architecture established during earlier phases.

---

## 2. AIService will become responsible for multiple generation stages.

Instead of one generation method, AIService will eventually coordinate:

- outline generation
    
- section generation
    
- merge generation
    

This keeps all LLM interactions inside a single service while allowing the pipeline itself to remain unchanged.

---

## 3. Avoid premature modelling.

An important engineering decision was made regarding the proposed `Outline` dataclass.

Although creating a structured model was initially suggested, it was intentionally postponed.

The reasoning was straightforward.

The project has not yet observed enough real outline outputs to determine what information an outline should consistently contain.

Rather than designing data structures based on assumptions, the project will first generate outlines from real educational material.

Only after observing repeated patterns will a formal `Outline` model be introduced.

This follows one of the project's broader architectural principles:

> **Design data models after understanding the data, not before.**

---

## 4. Preserve incremental development.

Rather than implementing the complete multi-stage generation pipeline immediately, development will proceed in small working increments.

The first objective is simply proving that reliable outlines can be generated.

Only then will section generation be adapted to use those outlines.

Finally, the merge stage will be introduced.

This incremental approach minimizes architectural risk while maintaining a continuously working application.

---

# Lessons Learned

Today's discussions reinforced several broader engineering principles.

### Infrastructure eventually stops being the bottleneck.

Once extraction, processing, and orchestration became stable, improvements shifted almost entirely toward AI reasoning and generation strategy.

---

### Prompt engineering alone has diminishing returns.

Continually refining prompts cannot compensate for structural limitations in the generation pipeline.

Architecture and generation strategy ultimately determine output quality more than individual prompt wording.

---

### Planning before writing is more powerful than preserving rolling context.

Providing every generation step with a shared understanding of the document is fundamentally stronger than passing only the previous section.

This insight may become the cornerstone of the project's future AI pipeline.

---

### Avoid premature abstraction.

Not every good idea should immediately become a new class or data model.

The project continues to favor evolving architecture only after repeated observations justify additional abstractions.

---

# Current Project Status

At the end of today's work:

- Infrastructure remains complete and stable.
    
- The application successfully processes large educational sources.
    
- Markdown generation is functioning correctly.
    
- Prompt engineering has reached a mature baseline.
    
- The project's primary focus has shifted toward document-planning strategies rather than prompt refinement.
    
- The next implementation milestone is prototyping an Outline Generation stage that precedes note generation.
    

This marks the transition from **building an application that uses an LLM** to **engineering a document generation system**. Future progress will depend less on adding backend components and more on designing an AI workflow that mirrors how skilled technical authors transform raw educational material into coherent, teachable knowledge.