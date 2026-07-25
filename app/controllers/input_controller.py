# This file just prepares the input. It does not do any other modifications.
# It converts urls, forms into KnowledgeCollection objects so that the rest of the pipeline can work with it.

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

        upload_folder = Path("uploads") # A Path knows how to join folders correctly on Windows, Linux, and macOS.
        upload_folder.mkdir(exist_ok=True) # Create the uploads folder if it doesn't already exist.

        for file in request.files.getlist("files"): # Loops through all the uploaded files.
            if file.filename == "":
                continue

            filename = secure_filename(file.filename) # Cleans the filename: ../../secret.txt -> secret.txt
            filepath = upload_folder / filename # Saves the file (HTTP request).
            file.save(filepath) # Saves it in disk.

            source = SourceFactory.from_upload_file(file)
            source.metadata["path"] = str(filepath) # Storing the filepath.

            collection.sources.append(source)

        urls = request.form.get("urls", "")

        for url in urls.splitlines(): # Splits by new lines.
            url = url.strip() # Removes spaces.

            if not url:
                continue

            source = SourceFactory.from_url(url)
            source.metadata["url"] = url

            collection.sources.append(source)

        return self.pipeline.process(collection, fast_model=fast_model)