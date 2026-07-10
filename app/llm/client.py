import os

from groq import Groq
from dotenv import load_dotenv
from app.llm.models import LLMRequest, LLMResponse

load_dotenv()

class GroqClient:
    def __init__(self) -> None:
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def generate(self, request: LLMRequest, model="llama-3.3-70b-versatile"):
        response = self.client.chat.completions.create( # Initialises request and sends it to groq
            model=model, messages=[
                {
                    "role" : "system",  # Tells the Ai what it is.
                    "content" : request.system_prompt
                },
                {
                    "role" : "user",
                    "content" : request.user_prompt
                }
            ])
        
      
        raw_content = response.choices[0].message.content or ""  # We get huge data back from groq, choices is the list of possible replies, 
        return LLMResponse(raw_output=raw_content)               # message is the part that contains text and content extracts that text.
         