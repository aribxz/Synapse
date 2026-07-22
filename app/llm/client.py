import os
import re
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from groq import Groq
from dotenv import load_dotenv
from app.llm.models import LLMRequest, LLMResponse
from config import Config

load_dotenv()

class GroqClient:
    def __init__(self) -> None:
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )

    def generate(self, request: LLMRequest, model: str):
        print(f"Using model: {model}", flush=True)

        kwargs = dict(
            model=model,
            messages=[
                {
                    "role" : "system",
                    "content" : request.system_prompt
                },
                {
                    "role" : "user",
                    "content" : request.user_prompt
                }
            ],
        )
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        response = self.client.chat.completions.create(**kwargs)
        
        print("Generation successful.", flush=True)
        
        raw_content = response.choices[0].message.content or "" 
        # We get huge data back from groq, choices is the list of possible replies, message is the part that contains text and content extracts that text. 
        
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        raw_content = re.sub(
                r"<think>.*?(?:</think>|$)",
                "",
                raw_content,
                flags=re.DOTALL,
        ).strip()

        return LLMResponse(raw_output=raw_content, usage=usage)               
         