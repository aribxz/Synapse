import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.knowledge_collection import KnowledgeCollection
from app.models.knowledge_source import KnowledgeSource
from app.models.enums import SourceType
from app.services.pipeline_service import PipelineService


class PipelineServiceTests(unittest.TestCase):
    def test_pipeline_handles_ai_failure_without_crashing(self):
        source = KnowledgeSource(
            source_type=SourceType.PDF,
            title="Sample PDF",
            raw_content="A " * 400,
            metadata={},
        )
        collection = KnowledgeCollection(sources=[source])
        pipeline = PipelineService()

        with patch.object(pipeline.ai, "generate_outline", side_effect=RuntimeError("boom")):
            output_file = pipeline.process(collection)

        self.assertTrue(Path(output_file).exists())

    def test_pipeline_handles_merge_failure_without_crashing(self):
        source = KnowledgeSource(
            source_type=SourceType.PDF,
            title="Sample PDF",
            raw_content="A " * 400,
            metadata={},
        )
        collection = KnowledgeCollection(sources=[source])
        pipeline = PipelineService()

        with patch.object(pipeline.ai, "generate_outline", return_value=[]), \
             patch.object(pipeline.ai, "generate_from_chunks", return_value=["Section content"]), \
             patch.object(pipeline.ai, "merge_sections", side_effect=RuntimeError("merge boom")):
            output_file = pipeline.process(collection)

        self.assertTrue(Path(output_file).exists())


if __name__ == "__main__":
    unittest.main()
