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

# --- Public demo rate limits ------------------------------------------------
# The public demo generates on CPU: one answer costs seconds to tens of seconds
# of the whole box. Limits are enforced in two scopes at once (see rate_limit.py)
# and every rule must pass. Raise these here if the demo needs more headroom —
# they are also the numbers shown to visitors in the frontend demo notice
# (RAG/src/components/DemoNotice.jsx), so keep the two in sync.
#
# Format: (limit, window in seconds, scope, label)
DEMO_RATE_LIMITS = [
    (1, 1, "ip", "second"),        # one question at a time per visitor
    (3, 60, "ip", "minute"),
    (10, 86_400, "ip", "day"),
    (3, 1, "global", "second"),    # whole-server ceiling
    (5, 60, "global", "minute"),
    (100, 86_400, "global", "day"),
]

# The external (server-to-server) endpoint used by the Vera landing page widget
# is not part of the public demo budget — it has its own, looser per-caller limit.
EXTERNAL_API_RATE_LIMITS = [
    (20, 60, "ip", "minute"),
]

# The app listens on 127.0.0.1 behind nginx, so request.client.host is always
# the proxy. Trust X-Forwarded-For so per-visitor limits key on the real client.
# ONLY safe because nothing but the local reverse proxy can reach the port —
# set to False if the app is ever exposed directly to the internet.
TRUST_FORWARDED_FOR = True
