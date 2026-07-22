import json
from flask import Blueprint, render_template, request, Response, stream_with_context

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

@main_bp.route("/about")
def about():
    return render_template("about.html")

@main_bp.route("/process", methods=["POST"])
def process():
    fast_model = request.form.get("fast_model", "gemini")
    print(f"--- Starting Processing Pipeline (fast model: {fast_model}) ---", flush=True)

    gen = controller.process_request(request, fast_model=fast_model)

    def generate():
        nonlocal gen
        try:
            while True:
                pct, msg, title = next(gen)
                yield json.dumps({"pct": pct, "msg": msg, "title": title}) + "\n"
        except StopIteration as e:
            output_file = e.value

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
        yield json.dumps({"type": "file", "content": content, "filename": "notes.md"}) + "\n"

    return Response(stream_with_context(generate()), mimetype="text/plain")

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
