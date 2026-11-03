from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)

from app.model import llm
from app.prompts import SYSTEM_PROMPT


def ask_ai(chat_history, user_message, preferences=""):
    system_prompt = SYSTEM_PROMPT

    if preferences.strip():
        system_prompt += (
            "\n\nUser preferences:\n" + preferences
        )

    messages = [
        SystemMessage(content=system_prompt)
    ]

    # Add previous messages so the AI has context.
    for message in chat_history:
        if message["role"] == "user":
            messages.append(
                HumanMessage(content=message["content"])
            )
        elif message["role"] == "assistant":
            messages.append(
                AIMessage(content=message["content"])
            )

    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)

    return response.content