"""Shared Foundry Local SDK setup.

Initializes the Foundry Local manager once and exposes lazily-loaded
embedding and chat clients so ingest/retrieval/answer can share them.
"""

from foundry_local_sdk import Configuration, FoundryLocalManager

import config

_manager = None
_embedding_client = None
_chat_client = None


def _get_manager():
    global _manager
    if _manager is None:
        FoundryLocalManager.initialize(Configuration(app_name="vera_rag"))
        _manager = FoundryLocalManager.instance
    return _manager


def _load_model(alias: str):
    manager = _get_manager()
    model = manager.catalog.get_model(alias)
    if not model.is_cached:
        print(f"Model '{alias}' is not downloaded yet — downloading now (one time only)...")
        model.download(lambda p: print(f"\r  {p:.1f}%", end="", flush=True))
        print()
    model.load()
    return model


def get_embedding_client():
    global _embedding_client
    if _embedding_client is None:
        model = _load_model(config.EMBEDDING_MODEL_ALIAS)
        _embedding_client = model.get_embedding_client()
    return _embedding_client


def get_chat_client():
    global _chat_client
    if _chat_client is None:
        model = _load_model(config.CHAT_MODEL_ALIAS)
        _chat_client = model.get_chat_client()
        _chat_client.settings.max_tokens = config.MAX_TOKENS
        _chat_client.settings.temperature = config.TEMPERATURE
        _chat_client.settings.frequency_penalty = config.FREQUENCY_PENALTY
        if hasattr(_chat_client.settings, "presence_penalty"):
            _chat_client.settings.presence_penalty = config.PRESENCE_PENALTY
    return _chat_client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, returning one vector per input."""
    client = get_embedding_client()
    response = client.generate_embeddings(texts)
    return [item.embedding for item in response.data]


def embed_text(text: str) -> list[float]:
    """Embed a single text."""
    client = get_embedding_client()
    response = client.generate_embedding(text)
    return response.data[0].embedding
