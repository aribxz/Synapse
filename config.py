# Config is the office
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key") 
    GROQ_API_KEY =  os.getenv("GROQ_API_KEY")

    LLM_PROVIDER = os.getenv(
        "LLM_PROVIDER",
        "groq"
    )

    FAST_MODEL = os.getenv(
        "FAST_MODEL",
        "llama-3.3-70b-versatile"
    )

    REASONING_MODEL = os.getenv(
        "REASONING_MODEL",
        "openai/gpt-oss-120b"
    )

