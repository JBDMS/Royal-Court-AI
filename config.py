from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("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")

MODEL_NAME = "openai/gpt-oss-20b"

TEMPERATURE = 0.7

MAX_TOKENS = 1024
