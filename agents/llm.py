from typing import Optional

from langchain_ollama import ChatOllama

from agents.config import CHAT_MODEL, OLLAMA_BASE_URL


def get_llm(temperature: float = 0.0, tags: Optional[list[str]] = None) -> ChatOllama:
    return ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
        tags=tags,
    )