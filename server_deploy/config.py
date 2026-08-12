"""Central configuration for the Vera-Finance server-hosted RAG assistant."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# Ollama (local, OpenAI-compatible REST API on this same server)
OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
EMBEDDING_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5:1.5b"

# Data locations
DOCS_DIR = PROJECT_ROOT / "docs_vera"
DB_PATH = PROJECT_ROOT / "vera_rag.db"

# Retrieval settings
TOP_K = 3          # fewer chunks = smaller prompt = faster CPU prompt-eval (dominant cost of time-to-first-token)

# Generation settings
MAX_TOKENS = 250          # hard cap — prevents runaway generation on small models; also bounds CPU-inference latency
TEMPERATURE = 0.1
FREQUENCY_PENALTY = 0.8   # penalize repeated tokens — curbs degeneration loops
PRESENCE_PENALTY = 0.6    # push the model off a token once it's been used at all
