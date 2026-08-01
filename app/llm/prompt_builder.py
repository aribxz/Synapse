# The main motive of this file is to make sure the LLM receives knowledge in a manner which maximizes its capablities to build good notes. 

from app.llm.models import LLMRequest
from app.llm.prompts.outline import OUTLINE_PROMPT
from app.llm.prompts.transition import TRANSITION_PROMPT
from app.llm.prompts.document_structure import DOCUMENT_STRUCTURE_PROMPT
from app.llm.outline_parser import OutlineTopic
from app.llm.prompts.teaching import TEACHING_PROMPT
from app.llm.prompts.extraction import EXTRACTION_PROMPT
from app.llm.knowledge_models import ExtractedKnowledge

import json
from dataclasses import asdict


class PromptBuilder:
    def _format_outline(self, outline: list[OutlineTopic]) -> str:
        """Helper method to turn our outline list into clean bullet points"""
        return "\n".join([f"- {topic.title} ({topic.role})" for topic in outline]) # Takes away the important part out of the outlines.

    def build_outline(self, chunks) -> LLMRequest:
        n = len(chunks)

        if n <= 8: # Solving one of the most important problems in this project, which is managing topics by the need.
            min_t, max_t = 3, 5

        elif n <= 20:
            min_t, max_t = 5, 9

        elif n <= 40:
            min_t, max_t = 8, 13

        else:
            min_t, max_t = 12, 18

        system_prompt = OUTLINE_PROMPT.format(NUM_CHUNKS=n, MIN_TOPICS=min_t, MAX_TOPICS=max_t) # Calls the prompt for that specific min/max topics.

        formatted_chunks = []

        for index, chunk in enumerate(chunks): # Giving good info to the LLM for it to work well.
            formatted_chunks.append(
                                    f"""
                        ===== CHUNK {index + 1} =====

                        {chunk.text}
                        """
                                )

        combined_text = "\n".join(formatted_chunks)

        user_prompt = f"""
                        Analyze the following educational material.

                        Identify the major topics.

                        For every topic include:

                        - Title
                        - Description
                        - Role
                        - Source Chunk(s)

                        Material:

                        {combined_text}
                    """

        return LLMRequest( # Finally handling the AI the efficient request.
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
        )

    def build_transition(self, prev_tail: str, next_head: str) -> LLMRequest: # Just tells gemini to write a transition.
        return LLMRequest(
            system_prompt=TRANSITION_PROMPT,
            user_prompt=f"=== END OF PREVIOUS SECTION ===\n{prev_tail}\n\n=== START OF NEXT SECTION ===\n{next_head}",
            max_tokens=256,
        )

    def build_document_structure(self, full_document: str, total_words: int) -> LLMRequest: # This is to keep record which helps at the end for the glossary table.
        return LLMRequest(
            system_prompt=DOCUMENT_STRUCTURE_PROMPT,
            user_prompt=f"This document has approximately {total_words} words.\n\nFull document:\n{full_document}",
            max_tokens=2048,
        )

    def build_extraction(self, text: str) -> LLMRequest:

        return LLMRequest(
            system_prompt=EXTRACTION_PROMPT,
            user_prompt=text,
        )
    
    def build_teaching(
    self,
    knowledge: ExtractedKnowledge,
    outline: list[OutlineTopic],
    current_topic: OutlineTopic,
    topic_index: int,
    total_topics: int,
    ) -> LLMRequest:

        knowledge_dict = {k: v for k, v in asdict(knowledge).items() if k != "connections"} # Remove connections because they are only needed during merge.
        knowledge_json = json.dumps(knowledge_dict, separators=(",", ":")) # Unpacks into a json because LLM's understand those very well.
        outline_text = self._format_outline(outline) # Uses the helper function to generate formatted outlines.

        user_prompt = f"""
                        DOCUMENT OUTLINE

                        {outline_text}

                        CURRENT TOPIC

                        Title: {current_topic.title}

                        Description: {current_topic.description}

                        Role: {current_topic.role}

                        Topic {topic_index + 1} of {total_topics}

                        EXTRACTED KNOWLEDGE

                        {knowledge_json}
                     """

        return LLMRequest(
            system_prompt=TEACHING_PROMPT,
            user_prompt=user_prompt,
        )