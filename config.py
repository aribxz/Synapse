# Config is the office
import os  # Bridge between os and computer system.

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key") 
    GROQ_API_KEY =  os.getenv("GROQ_API_KEY")

    LLM_PROVIDER = os.getenv(
        "LLM_PROVIDER",
        "groq"
    )

    FAST_MODEL = os.getenv(
        "FAST_MODEL",
        "qwen/qwen3-32b"
    )

    REASONING_MODEL = os.getenv(
        "REASONING_MODEL",
        "openai/gpt-oss-120b"
    )

