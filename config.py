import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

    FAST_MODEL = os.getenv("FAST_MODEL", "llama-3.3-70b-versatile")
    GEMINI_FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", "gemini-3.1-flash-lite")
    REASONING_MODEL = os.getenv("REASONING_MODEL", "openai/gpt-oss-120b")

    @classmethod
    def validate(cls):
        missing = []

        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Add them to your .env file."
            )
