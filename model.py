from langchain_groq import ChatGroq

from app.config import (
    GROQ_API_KEY,
    MODEL_NAME,
    TEMPERATURE,
)

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=MODEL_NAME,
    temperature=TEMPERATURE,
)