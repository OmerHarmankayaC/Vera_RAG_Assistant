"""Central configuration for the Vera-Finance local RAG assistant."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# Foundry Local model aliases (see `foundry model list` / SDK catalog)
EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"
CHAT_MODEL_ALIAS = "qwen2.5-1.5b"

# Data locations
DOCS_DIR = PROJECT_ROOT / "docs_vera"
DB_PATH = PROJECT_ROOT / "vera_rag.db"

# Retrieval settings
TOP_K = 5                 # enough breadth for overview ("what can the app do?") questions

# Generation settings
MAX_TOKENS = 300          # hard cap — prevents runaway generation on small models
TEMPERATURE = 0.1
FREQUENCY_PENALTY = 0.8   # penalize repeated tokens — curbs degeneration loops
PRESENCE_PENALTY = 0.6    # push the model off a token once it's been used at all
