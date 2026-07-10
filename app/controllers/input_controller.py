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

    def process_request(self, request):
        collection = KnowledgeCollection()
        
        upload_folder = Path("uploads") # checks for a uploads folder if not creates it
        upload_folder.mkdir(exist_ok=True) # bypass if it already exists

        for file in request.files.getlist("files"):
            # getlist : I know there might be more than one item under this label, so please go ahead and gather all of them into a list for me.
            # request.files is a html attribute
            if file.filename == "": # if the user selected upload but there is no file
                continue

            filename = secure_filename(file.filename) # security check for / characters
            filepath = upload_folder / filename # Take this directory path and append this filename to it with the correct slash character
            file.save(filepath)

            source = SourceFactory.from_upload_file(file) #Source Factory allows it to know what format it is
            source.metadata["path"] = str(filepath)

            collection.sources.append(source) 

        urls = request.form.get("urls", "") # Grabs the text from the "urls" input box on your webpage

        for url in urls.splitlines():
            url = url.strip() # removes accidental spaces

            if not url:
                continue

            source = SourceFactory.from_url(url)
            source.metadata["url"] = url

            collection.sources.append(source)

        output = self.pipeline.process(collection)
        return output