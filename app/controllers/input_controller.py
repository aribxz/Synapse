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

    def process_request(self, request, fast_model="gemini"):
        collection = KnowledgeCollection()

        upload_folder = Path("uploads")
        upload_folder.mkdir(exist_ok=True)

        for file in request.files.getlist("files"):
            if file.filename == "":
                continue

            filename = secure_filename(file.filename)
            filepath = upload_folder / filename
            file.save(filepath)

            source = SourceFactory.from_upload_file(file)
            source.metadata["path"] = str(filepath)

            collection.sources.append(source)

        urls = request.form.get("urls", "")

        for url in urls.splitlines():
            url = url.strip()

            if not url:
                continue

            source = SourceFactory.from_url(url)
            source.metadata["url"] = url

            collection.sources.append(source)

        return self.pipeline.process(collection, fast_model=fast_model)