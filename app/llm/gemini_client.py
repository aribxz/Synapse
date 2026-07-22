import os
import re
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from google.genai import Client as GenaiClient
from google.genai import types
from dotenv import load_dotenv
from app.llm.models import LLMRequest, LLMResponse

load_dotenv()


class GeminiClient:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Add it to your .env file."
            )
        self.client = GenaiClient(api_key=api_key)

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def generate(self, request: LLMRequest, model: str):
        print(f"Using model: {model}", flush=True)

        config_kwargs = dict(
            system_instruction=request.system_prompt,
        )
        if request.max_tokens is not None:
            config_kwargs["max_output_tokens"] = request.max_tokens

        response = self.client.models.generate_content(
            model=model,
            contents=request.user_prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        print("Generation successful.", flush=True)

        raw_content = response.text or ""

        usage = {}
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }

        raw_content = re.sub(
            r"<think>.*?</think>",
            "",
            raw_content,
            flags=re.DOTALL,
        ).strip()

        return LLMResponse(raw_output=raw_content, usage=usage)
