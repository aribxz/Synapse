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
    print("--- Starting Processing Pipeline ---", flush=True)
    output_file = controller.process_request(request)
    print(f"--- Extraction Finished, Processing sources ---", flush=True)

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

