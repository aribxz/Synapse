### Concept Explanation: The "Map-Reduce" pattern.
In production LLM systems (like yours), when you have a massive document, you can't just "ask" the AI about it. You use a pattern called **Map-Reduce**:

- **Map:** You break the document into chunks and have the AI "map" out what is in each chunk (your **Outline** phase).
    
- **Reduce:** You take only the relevant chunks and "reduce" them into a final answer (your **Extraction/Teaching** phase).
    

This is why your OutlineParser is the "brain" of the operation. If the outline is bad, the whole study guide fails, even if the individual chunks are perfect.

---
### Concept Explanation: The "Ticket Counter" Pattern

In production systems, this is handled like a deli or a repair shop:

1. **The Request (The Ticket):** When the user clicks "Process," the InputController doesn't start the work. It saves the KnowledgeCollection to a **Database** and returns a "Ticket ID" (a Unique ID) to the user's browser immediately.
    
2. **The Worker (The Backend):** A separate background process (often called a **Worker**, using tools like Celery or Redis) sees the new entry in the database and starts the PipelineService independently of the web server.
    
3. **The Status (The Progress Bar):** As the PipelineService moves through chunks, it updates the status field in the database (e.g., status: "Processing Topic 3...").
    
4. **The Polling (The UI):** The user's browser (using a bit of JavaScript) "polls" or asks the server every 2 seconds: "Is Ticket #123 done yet? What is the status?" and updates the progress bar.