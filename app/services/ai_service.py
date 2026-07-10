from app.llm.client import GroqClient
from app.llm.prompt_builder import PromptBuilder
from app.llm.outline_parser import OutlineParser
from app.llm.extraction_parser import ExtractionParser

class AIService:
    def __init__(self):
        self.client = GroqClient()
        self.prompt_builder = PromptBuilder()

    def generate_from_chunks(self, chunks, outline):
        outputs = []
        previous_notes = None
        total_topics = len(outline)

        for topic_index, topic in enumerate(outline):
            source_text = self._collect_topic_text(topic, chunks)

            try:
                extraction_request = self.prompt_builder.build_extraction(source_text)
                raw_json = self.client.generate(extraction_request).raw_output

                knowledge = ExtractionParser().parse(raw_json)

                teaching_request = self.prompt_builder.build_teaching(
                    knowledge=knowledge,
                    outline=outline,
                    current_topic=topic,
                    previous_notes=previous_notes,
                    topic_index=topic_index,
                    total_topics=total_topics,
                )

                response = self.client.generate(teaching_request)

                outputs.append(response.raw_output)
                previous_notes = response.raw_output

            except Exception as e:
                print(f"Generation failed: {e}")
                continue

        return outputs
    
    def generate_outline(self, chunks):
        request = self.prompt_builder.build_outline(chunks)
        response = self.client.generate(request)
        return OutlineParser().parse(response.raw_output)
    
    def merge_sections(self, sections):
        request = self.prompt_builder.build_merge(sections)
        response = self.client.generate(request)
        return response.raw_output
    
    def _collect_topic_text(self, topic, chunks):
        selected = []

        for index in topic.source_chunks:
            if 1 <= index <= len(chunks):
                selected.append(chunks[index - 1].text)

        return "\n\n".join(selected)