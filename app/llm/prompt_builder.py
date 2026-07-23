from app.llm.models import LLMRequest
from app.llm.prompts import STUDY_NOTES_PROMPT
from app.llm.prompts.outline import OUTLINE_PROMPT
from app.llm.prompts.merge import MERGE_PROMPT
from app.llm.outline_parser import OutlineTopic
from app.llm.prompts.teaching import TEACHING_PROMPT
from app.llm.prompts.extraction import EXTRACTION_PROMPT
from app.llm.knowledge_models import ExtractedKnowledge

import json
from dataclasses import asdict


class PromptBuilder:
    def _format_outline(self, outline: list[OutlineTopic]) -> str:
        """Helper method to turn our outline list into clean bullet points"""
        return "\n".join([f"- {topic.title} ({topic.role})" for topic in outline])

    def build_outline(self, chunks) -> LLMRequest:

        n = len(chunks)
        if n <= 8:
            min_t, max_t = 3, 5
        elif n <= 20:
            min_t, max_t = 5, 9
        elif n <= 40:
            min_t, max_t = 8, 13
        else:
            min_t, max_t = 12, 18

        system_prompt = OUTLINE_PROMPT.format(NUM_CHUNKS=n, MIN_TOPICS=min_t, MAX_TOPICS=max_t)

        formatted_chunks = []

        for index, chunk in enumerate(chunks):
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

        return LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
        )

    def build(
        self,
        text: str,
        outline: list[OutlineTopic],
        current_topic: OutlineTopic,
        topic_index: int,
        total_topics: int,
        previous_notes: str | None = None,
    ) -> LLMRequest:

        previous_section = previous_notes or "None (this is the first section)."

        outline_text = "\n".join(
            [
                f"- {topic.title} ({topic.role})"
                for topic in outline
            ]
        )

        user_prompt = f"""
                            DOCUMENT OUTLINE

                            {outline_text}

                            CURRENT TOPIC

                            Title:
                            {current_topic.title}

                            Description:
                            {current_topic.description}

                            Role:
                            {current_topic.role}

                            Topic {topic_index + 1} of {total_topics}

                            PREVIOUS SECTION

                            {previous_section}

                            YOUR RESPONSIBILITY

                            Write this section according to its role.

                            If the role is Motivation:
                            Explain why this topic exists before explaining how it works.

                            If the role is Intuition:
                            Help the reader build an intuitive mental model.

                            If the role is Mechanism:
                            Explain the complete process step-by-step.

                            If the role is Procedure:
                            Describe the algorithm or workflow clearly.

                            If the role is Example:
                            Focus on demonstrating the concept.

                            If the role is Edge Case:
                            Explain limitations, assumptions and special cases.

                            If the role is Takeaway:
                            Summarize the important lessons and connect them to earlier topics.

                            TASK

                            Using ONLY the source content below:

                            - Teach the material instead of summarizing it.
                            - Follow the document outline.
                            - Expand ideas when necessary.
                            - Explain the reasoning behind important steps.
                            - Define technical terms on first use.
                            - Avoid repeating previous sections.
                            - Assume this section will later be merged into one complete study guide.

                            SOURCE CONTENT

                            {text}
                        """

        return LLMRequest(
            system_prompt=STUDY_NOTES_PROMPT,
            user_prompt=user_prompt,
        )
    
    def build_merge(self, sections: list[str], connections_info: str | None = None) -> LLMRequest:
        combined = "\n\n".join(sections)

        extra_context = ""
        if connections_info:
            extra_context = f"""
CROSS-TOPIC CONNECTIONS (from extraction)

The following cross-topic relationships were identified. Use them to ensure consistent terminology and to link related sections:

{connections_info}

"""

        user_prompt = f"""
                        {extra_context}Merge the following study guide sections into one polished document.

                        Study Guide Sections

                        {combined}
                    """

        return LLMRequest(
            system_prompt=MERGE_PROMPT,
            user_prompt=user_prompt,
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

        knowledge_dict = {k: v for k, v in asdict(knowledge).items() if k != "connections"}
        knowledge_json = json.dumps(knowledge_dict, separators=(",", ":"))
        outline_text = self._format_outline(outline)

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