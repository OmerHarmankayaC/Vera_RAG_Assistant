"""Shared Ollama client setup — Ollama's OpenAI-compatible local REST API."""

from openai import OpenAI

import config

_client = OpenAI(base_url=config.OLLAMA_BASE_URL, api_key="ollama")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, returning one vector per input."""
    response = _client.embeddings.create(model=config.EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def embed_text(text: str) -> list[float]:
    """Embed a single text."""
    return embed_texts([text])[0]


def complete_chat(messages: list[dict]):
    return _client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=messages,
        max_tokens=config.MAX_TOKENS,
        temperature=config.TEMPERATURE,
        frequency_penalty=config.FREQUENCY_PENALTY,
        presence_penalty=config.PRESENCE_PENALTY,
    )


def complete_streaming_chat(messages: list[dict]):
    return _client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=messages,
        max_tokens=config.MAX_TOKENS,
        temperature=config.TEMPERATURE,
        frequency_penalty=config.FREQUENCY_PENALTY,
        presence_penalty=config.PRESENCE_PENALTY,
        stream=True,
    )
