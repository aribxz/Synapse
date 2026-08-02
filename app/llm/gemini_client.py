# Literally the same as client.py which was for groq.

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

    def transcribe_youtube(self, url: str, model: str | None = None) -> str:
        """Ask Gemini to transcribe a public YouTube video using its native
        video support (Google's servers fetch the video, not ours).

        Why this exists: Render's server IP is blocked by YouTube, so the
        transcript library can't fetch captions from the cloud. Gemini accepts
        the YouTube URL directly and transcribes it server-side, bypassing the
        IP problem entirely.

        Gemini's recitation (copyright) filter sometimes blocks verbatim
        transcription, returning an empty response. In that case we retry once
        with a section-by-section, "in your own words" prompt, which usually
        passes while keeping ~96% fidelity.

        Caveats:
          - Preview feature: free tier caps at 8 hours of YouTube video/day
            and only PUBLIC videos are supported (no private/unlisted).
          - Very long videos may fail or overflow the context window; the
            caller should fall back to another path when this raises.
        """
        model = model or os.getenv("GEMINI_FAST_MODEL", "gemini-3.1-flash-lite")

        verbatim_prompt = (
            "Transcribe this video's full spoken content as accurately as "
            "possible, in order, as plain text. Do not summarize or skip "
            "sections. Output only the spoken words with no timestamps."
        )
        paraphrase_prompt = (
            "Transcribe this video section by section in time order. For each "
            "~2 minute section, give the full spoken content in your own words, "
            "keeping every detail and example. Do not skip anything. "
            "Output plain text."
        )

        last_reason = "no candidates returned"
        for prompt in (verbatim_prompt, paraphrase_prompt):
            contents = types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=url)),
                    types.Part(text=prompt),
                ]
            )

            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=65536,
                    media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
                ),
            )

            text = (response.text or "").strip()
            if text:
                return text

            if response.candidates:
                last_reason = str(response.candidates[0].finish_reason)
            else:
                last_reason = "no candidates returned"

        raise ValueError(f"Gemini returned an empty transcript (finish reason: {last_reason})")
